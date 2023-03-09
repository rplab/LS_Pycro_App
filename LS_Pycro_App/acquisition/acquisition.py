"""
Main acquisition script. This class takes all the data initialized using the AcquisitionRegionsDialog 
window and performs an image acquisition based on said data. It is created in a new thread so the user 
isn't locked out from GUI interaction during acquisition.

Future Changes:
- True stage positions included in Metadata in cont_z_stack_acquisition(). Currently every device property 
is in there. Not really sure how to do this because stage would need to be queried but the stage is always 
moving and doesn't take other commands while it's scanning!

- In addition to the issue above, cont_z_stack_acquisition() currently sets a buffer at the end of the scan to ensure 
camera captures enough images to match the number of expected images in the sequence acquisition. Without this buffer,
the acquisition fails sometimes because the camera doesn't capture enough images. This implies that there's some sort of
timing issue with the triggering, either from the stage TTL signal or the PLC. I'm guessing it has something to do with
the PLC not sending a trigger to the camera until both delays have been passed. I bet if I send the trigger to the 
camera before going to the delays, I could fix this. 

This just means that the absolute start and end positions are offset by some amount, which is fine because we only care 
about relative positions (ie, it doesn't matter if the true start position is 1300 vs 1303 um, as long as ALL of the 
start/end positions are also offset by the same 3 um, which should be the case unless this is some inconsistency in the 
stage TTL signal itself, which I very highly doubt).

- Possibly change all image acquisiton to Pycro-Manager acquisition. Not really sure if this is worth the trouble.

- Clean up/documentation!

- Figure out if exception handling  is good enough.
"""

import logging
import threading
import os
from abc import ABC, abstractmethod
from acquisition.acquisition_sequences import TimeSampAcquisition, SampTimeAcquisition, PositionTimeAcquisition
from hardware import stage, camera, plc
from models.acquisition.acq_settings import AcqSettings
from models.acquisition.adv_settings import AcqOrder
from models.acquisition.acq_directory import AcqDirectory
from utils import exceptions, user_config
from utils.pycro import core, studio
from views.shared import AbortDialog, AcqDialog


class Acquisition(threading.Thread, ABC):
    """
    Contains all implementation of imaging sequences. Inherits Thread, so to start acquisition, call
    start().

    ## Constructor parameters:

    #### acq_settings : AcquisitionSettings
        AcquisitionSettings instance that contains all image acquisition settings. 

    """
    @abstractmethod
    def _init_additional_hardware(self):
        """
        Initializes hardware to state required for acquisition.
        """
    
    @abstractmethod
    def _write_settings_to_config(self):
        """
        Write finalized settings to user_config when acquisition begins.
        """
        pass

    def __init__(self, acq_settings: AcqSettings):
        super().__init__()

        self._logger = logging.getLogger(self.__class__.__name__)
        #Reason for this deepcopy is so if settings are changed in the GUI while an acquisition is running,
        #it won't change the settings in the middle of the acquisition
        self._acq_settings = acq_settings
        self._adv_settings = self._acq_settings.adv_settings

        self._abort_dialog = AbortDialog()
        self._acq_dialog = AcqDialog()
        self._abort_flag = exceptions.AbortFlag()

        self._acq_dialog.abort_button.clicked.connect(self._abort_button_clicked)
        self._abort_dialog.cancel_button.clicked.connect(self._cancel_button_clicked)
        self._abort_dialog.abort_button.clicked.connect(self._abort_confirm_button_clicked)

    def run(self):
        """
        This method runs an image acquisition with the data store in the instance
        of acquisition_settings. Currently, acquires combinations of snaps, videos
        and z-stacks.

        This method is called when Acquisition.start() is called and runs in a 
        separate thread.

        There are currently two acquisitions orders which are chosen with the
        AcquisitionOrder Enum class:

        TIME_SAMP - Normal time series acquisition. Each time point consists of imaging
        of all samples in sequence, after which it will wait until the next time point
        and repeat.
        
        SAMP_TIME - An entire time series will be executed for the first sample, then 
        another time series for the next sample, and so on. 
        """
        try:
            self._status_update("Initializing Acquisition")
            self._init_core_settings()
            self._init_plc()
            self._init_additional_hardware()

            acq_directory = AcqDirectory(self._acq_settings.directory)
            os.makedirs(acq_directory.root)
            self._write_acquisition_notes(acq_directory)

            self._abort_flag.abort = False
            self._start_acquisition(acq_directory)
        except exceptions.AbortAcquisitionException:
            self._abort_acquisition(self._abort_flag.abort)
        except:
            self._logger.exception("exception raised during acquisition")
            self._abort_acquisition(self._abort_flag.abort)
        else:
            self.hardware_reset()
            studio.app().refresh_gui()
            self._status_update("Your acquisition was successful!")

    def _init_core_settings(self):
        core.stop_sequence_acquisition()
        core.clear_circular_buffer()
        core.set_shutter_open(False)
        core.set_auto_shutter(True)

    def _init_plc(self):
        """
        Initializes plc to z-stack settings of first region.
        """
        stage_speed = self._acq_settings.adv_settings.z_stack_stage_speed
        step_size = self._acq_settings.fish_list[0].region_list[0].z_stack_step_size
        plc.set_plc_for_z_stack(step_size, stage_speed)

    def _write_acquisition_notes(self, acq_directory: AcqDirectory):
        """
        Writes current config as acquisition notes at acq_directory.root.
        """
        self._write_settings_to_config()
        user_config.write_config_file(f"{acq_directory.root}/notes.txt")

    #write_acquisition_notes helpers
    def _write_settings_to_config(self):
        """
        Writes updated settings to config.
        """
        self._acq_settings.write_to_config()

    def _start_acquisition(self, acq_directory: AcqDirectory):
        if self._adv_settings.acq_order == AcqOrder.TIME_SAMP:
            sequence = TimeSampAcquisition(self._acq_settings, self._acq_dialog, self._abort_flag, acq_directory)
        elif self._adv_settings.acq_order == AcqOrder.SAMP_TIME:
            sequence = SampTimeAcquisition(self._acq_settings, self._acq_dialog, self._abort_flag, acq_directory)
        elif self._adv_settings.acq_order == AcqOrder.POS_TIME:
            sequence = PositionTimeAcquisition(self._acq_settings, self._acq_dialog, self._abort_flag, acq_directory)
        
        
        sequence.run_acquisition()

    def _status_update(self, message:str):
        """
        Displays message on acquisition label and writes it to logs
        """
        self._acq_dialog.acq_label.setText(message)
        self._logger.info(message)

    #abort/exception implementation
    def _abort_button_clicked(self):
        self._abort_dialog.show()
        self._abort_dialog.activateWindow()

    def _abort_confirm_button_clicked(self):
        """
        If confirmed, acquisition will be aborted.
        """
        self._abort_dialog.close()
        self._abort_flag.abort = True
        self._abort_acquisition(self._abort_flag.abort)

    def _cancel_button_clicked(self):
        self._abort_dialog.close()

    def _abort_acquisition(self, acq_aborted: bool):
        """
        called when acquisition is aborted or failed. Stops sequence acquisition if one is running,
        clears circular buffer, sets the default camera properties, and resets the joystick. 
        """
        if acq_aborted:
            first_message = "Aborting Acquisition"
            second_message = "Aborted Acquisition"
        else:
            first_message = "Acquisition Failed. Stopping."
            second_message = "Acquisition Failed. Check Logs."

        self._status_update(first_message)
        self.hardware_reset()
        self._status_update(second_message)

    def hardware_reset(self):
        try:
            core.stop_sequence_acquisition()
        except:
            pass
        core.clear_circular_buffer()
        core.set_exposure(camera.DEFAULT_EXPOSURE)
        camera.set_burst_mode()
        stage.reset_joystick()
