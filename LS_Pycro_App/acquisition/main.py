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
from abc import ABC, abstractmethod
from copy import deepcopy

from LS_Pycro_App.acquisition.sequences import (
    AcquisitionSequence, TimeSampAcquisition, SampTimeAcquisition, PosTimeAcquisition, HTLSSequence)
from LS_Pycro_App.models.acq_directory import AcqDirectory
from LS_Pycro_App.hardware import Stage, Camera, Galvo, Plc
from LS_Pycro_App.models.acq_settings import AcqSettings, AcqOrder
from LS_Pycro_App.views import AbortDialog, AcqDialog
from LS_Pycro_App.models.acq_settings import HTLSSettings
from LS_Pycro_App.utils import exceptions, user_config
from LS_Pycro_App.utils.pycro import core, studio


class Acquisition(ABC, threading.Thread):
    """
    Contains all implementation of imaging sequences. Inherits Thread, so to start acquisition, call
    start().

    ## Constructor parameters:

    #### acq_settings : AcquisitionSettings
        AcquisitionSettings instance that contains all image acquisition settings. 

    """
    def __init__(self, acq_settings: AcqSettings | HTLSSettings):
        super().__init__()
        self._logger = logging.getLogger(self.__class__.__name__)
        #Reason for this deepcopy is so if settings are changed in the GUI while an acquisition is running,
        #it won't change the settings in the middle of the acquisition
        self._acq_settings = deepcopy(acq_settings)
        self._adv_settings = self._acq_settings.adv_settings
        self._acq_directory = AcqDirectory(self._acq_settings.directory)
        self._abort_dialog = AbortDialog()
        self._acq_dialog = AcqDialog()
        self._abort_flag = exceptions.AbortFlag()
        self._acq_dialog.abort_button.clicked.connect(self._abort_button_clicked)
        self._abort_dialog.cancel_button.clicked.connect(self._cancel_button_clicked)
        self._abort_dialog.abort_button.clicked.connect(self._abort_confirm_button_clicked)

    @abstractmethod
    def _get_acq_sequence(self) -> AcquisitionSequence:
        """
        This should return one of the classes that inherits from the AcquisitionSequence
        class in sequences.py file. For CLS acquisitions, this is determined by the
        acq_order attribute of AcqSettings, and for HTLS, it should be the HTLS sequence.
        """

    @abstractmethod
    def _init_hardware(self):
        """
        This method should initialize hardware devices for acquisition. Only devices that
        require some initial state need to be implemented, such as the PLC and the Galvos.
        """

    @abstractmethod
    def _reset_hardware(self):
        """
        This method should reset hardware to its pre-acquisition state.
        """

    def run(self):
        """
        This method runs an image acquisition with the parameters set in
        acq_settings.

        This method is called when Acquisition.start() is called and runs in a 
        separate thread.
        """
        try:
            self._status_update("Initializing Acquisition")
            self._init_hardware()
            self._abort_flag.abort = False
            sequence = self._get_acq_sequence()
            sequence.run()
        except exceptions.AbortAcquisitionException:
            self._abort_acquisition(self._abort_flag.abort)
        except:
            self._logger.exception("exception raised during acquisition")
            self._abort_acquisition(self._abort_flag.abort)
        else:
            self._write_acquisition_notes()
            self._reset_hardware()
            studio.app().refresh_gui()
            self._status_update("Your acquisition was successful!")
        
    def _init_mm(self):
        core.stop_sequence_acquisition()
        core.clear_circular_buffer()
        core.set_shutter_open(False)
        core.set_auto_shutter(True)
    
    def _write_acquisition_notes(self):
        """
        Writes current config as acquisition notes at acq_directory.root.
        """
        user_config.write_config_file(f"{self._acq_directory.root}/notes.txt")

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
        self._reset_hardware()
        self._status_update(second_message)


class CLSAcquisition(Acquisition):
    def _get_acq_sequence(self):
        if self._adv_settings.acq_order == AcqOrder.TIME_SAMP:
            return TimeSampAcquisition(self._acq_settings, self._acq_dialog, self._abort_flag, self._acq_directory)
        elif self._adv_settings.acq_order == AcqOrder.SAMP_TIME:
            return SampTimeAcquisition(self._acq_settings, self._acq_dialog, self._abort_flag, self._acq_directory)
        elif self._adv_settings.acq_order == AcqOrder.POS_TIME:
            return PosTimeAcquisition(self._acq_settings, self._acq_dialog, self._abort_flag, self._acq_directory)
        
    def _init_hardware(self):
        self._init_galvo()
        self._init_plc()

    def _init_galvo(self):
        if Galvo:
            Galvo.set_dslm_mode()

    def _init_plc(self):
        Plc.set_for_z_stack(self._acq_settings.get_first_step_size())

    def _reset_hardware(self):
        Plc.set_continuous_pulses(30)
        core.stop_sequence_acquisition()
        Camera.set_exposure(Camera.DEFAULT_EXPOSURE)
        Camera.set_burst_mode()
        Plc.init_pulse_mode()
        core.clear_circular_buffer()
        Stage.reset_joystick()


class HTLSAcquisition(Acquisition):
    def _get_acq_sequence(self):
        return HTLSSequence(self._acq_settings, self._acq_dialog, self._abort_flag, self._acq_directory)
        
    def _init_hardware(self):
        self._init_galvo()
        self._init_plc()

    def _init_galvo(self):
        if Galvo:
            Galvo.set_dslm_mode()

    def _init_plc(self):
        Plc.set_for_z_stack(self._acq_settings.region_settings.z_stack_step_size)

    def _reset_hardware(self):
        Plc.set_continuous_pulses(30)
        core.stop_sequence_acquisition()
        Camera.set_exposure(Camera.DEFAULT_EXPOSURE)
        Camera.set_burst_mode()
        Plc.init_pulse_mode()
        core.clear_circular_buffer()
        Stage.reset_joystick()
