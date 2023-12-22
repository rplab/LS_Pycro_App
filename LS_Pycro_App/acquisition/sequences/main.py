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
from copy import deepcopy

from LS_Pycro_App.acquisition.sequences.orders import TimeSampAcquisition, SampTimeAcquisition, PosTimeAcquisition
from LS_Pycro_App.acquisition.sequences.imaging import Video
from LS_Pycro_App.acquisition.models.acq_directory import AcqDirectory
from LS_Pycro_App.hardware import Stage, Camera, Galvo, Plc
from LS_Pycro_App.acquisition.models.acq_settings import AcqSettings
from LS_Pycro_App.acquisition.models.adv_settings import AcqOrder
from LS_Pycro_App.acquisition.models.acq_directory import AcqDirectory
from LS_Pycro_App.acquisition.views.py import AbortDialog, AcqDialog
from LS_Pycro_App.hardware import Galvo
from LS_Pycro_App.utils import exceptions, user_config
from LS_Pycro_App.utils.pycro import core, studio, BF_CHANNEL


class Acquisition(threading.Thread):
    """
    Contains all implementation of imaging sequences. Inherits Thread, so to start acquisition, call
    start().

    ## Constructor parameters:

    #### acq_settings : AcquisitionSettings
        AcquisitionSettings instance that contains all image acquisition settings. 

    """
    def __init__(self, acq_settings: AcqSettings):
        super().__init__()
        self._logger = logging.getLogger(self.__class__.__name__)
        #Reason for this deepcopy is so if settings are changed in the GUI while an acquisition is running,
        #it won't change the settings in the middle of the acquisition
        self._acq_settings = acq_settings
        self._adv_settings = self._acq_settings.adv_settings
        self._acq_directory = AcqDirectory(self._acq_settings.directory)
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
            self._init_mm_settings()
            self._init_galvo()
            os.makedirs(self._acq_directory)
            self._write_acquisition_notes()
            self._abort_flag.abort = False
            self._start_acquisition()
            self._status_update("taking end videos...")
            self._end_acquisition_video()
        except exceptions.AbortAcquisitionException:
            self._abort_acquisition(self._abort_flag.abort)
        except:
            self._logger.exception("exception raised during acquisition")
            self._abort_acquisition(self._abort_flag.abort)
        else:
            self.hardware_reset()
            studio.app().refresh_gui()
            self._status_update("Your acquisition was successful!")

    def _init_mm_settings(self):
        core.stop_sequence_acquisition()
        core.clear_circular_buffer()
        core.set_shutter_open(False)
        core.set_auto_shutter(True)

    def _init_galvo(self):
        if Galvo:
            Galvo.set_dslm_mode()

    def _init_plc(self):
        Plc.set_for_z_stack(self._acq_settings.get_first_step_size())
    
    def _write_acquisition_notes(self):
        """
        Writes current config as acquisition notes at acq_directory.root.
        """
        user_config.write_config_file(f"{self._acq_directory.root}/notes.txt")

    def _start_acquisition(self):
        acq_directory = deepcopy(self._acq_directory)
        if self._adv_settings.acq_order == AcqOrder.TIME_SAMP:
            sequence = TimeSampAcquisition(self._acq_settings, self._acq_dialog, self._abort_flag, acq_directory)
        elif self._adv_settings.acq_order == AcqOrder.SAMP_TIME:
            sequence = SampTimeAcquisition(self._acq_settings, self._acq_dialog, self._abort_flag, acq_directory)
        elif self._adv_settings.acq_order == AcqOrder.POS_TIME:
            sequence = PosTimeAcquisition(self._acq_settings, self._acq_dialog, self._abort_flag, acq_directory)
        sequence.run()

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
        Camera.set_exposure(Camera.DEFAULT_EXPOSURE)
        Camera.set_burst_mode()
        Stage.reset_joystick()


    def _end_acquisition_video(self):
        for fish_num, fish in enumerate(self._acq_settings.fish_list):
            if fish.imaging_enabled:
                region = deepcopy(fish.region_list[0])
                region.video_enabled = True
                region.video_exposure = 30
                region.video_num_frames = 125
                region.video_channel_list = [BF_CHANNEL]
                Stage.move_stage(region.x_pos, region.y_pos, region.z_pos)
                acq_directory = deepcopy(self._acq_directory)
                acq_directory.root = f"{acq_directory.root}/end_videos"
                acq_directory.set_fish_num(fish_num)
                acq_directory.set_region_num(0)
                acq_directory.set_time_point(0)
                video = Video(region, self._acq_settings, self._abort_flag, acq_directory)
                for update_message in video.run():
                    pass
