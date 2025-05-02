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

from LS_Pycro_App.acquisition.acq_gui import CLSAcqGui, HTLSAcqGui
from LS_Pycro_App.acquisition.sequences import (
    TimeSampAcquisition, SampTimeAcquisition, PosTimeAcquisition, HTLSSequence)
from LS_Pycro_App.models.acq_directory import AcqDirectory
from LS_Pycro_App.hardware import Stage, Camera, Galvo, Plc, Pump
from LS_Pycro_App.models.acq_settings import AcqSettings, AcqOrder
from LS_Pycro_App.models.acq_settings import HTLSSettings
from LS_Pycro_App.utils import constants, exceptions, user_config
from LS_Pycro_App.utils.pycro import core, studio


class Acquisition(ABC, threading.Thread):
    """
    Contains all implementation of imaging sequences. Inherits Thread, so to start acquisition, call
    start().

    ## Constructor parameters:

    #### acq_settings : AcquisitionSettings
        AcquisitionSettings instance that contains all image acquisition settings. 

    """
    @abstractmethod
    def run(self):
        """
        This method runs an image acquisition with the parameters set in
        acq_settings.

        This method is called when Acquisition.start() is called and runs in a 
        separate thread.
        """

    @abstractmethod
    def _abort_acquisition(self):
        """
        Method should be called when acquisition is aborted. If acquisition uses hardware, should reset
        hardware devices to initial states. Should also display to the GUI that the acquisition
        has been aborted.
        """
    
    def _init_mm(self):
        studio.live().set_live_mode_on(False)
        core.stop_sequence_acquisition()
        core.clear_circular_buffer()
        core.set_shutter_open(False)
        core.set_auto_shutter(True)

    def _write_acquisition_notes(self, root_directory: str):
        """
        Writes current config as acquisition notes at acq_directory.root.
        """
        user_config.write_config_file(f"{root_directory}/notes.txt")


class HardwareAcquisition(ABC):
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


class CLSAcquisition(Acquisition, HardwareAcquisition):
    def __init__(self, 
                 acq_settings: AcqSettings, 
                 acq_gui: CLSAcqGui, 
                 acq_directory: AcqDirectory,
                 abort_flag: exceptions.AbortFlag):
        #Reason for this deepcopy is so if settings are changed in the GUI while an acquisition is running,
        #it won't change the settings in the middle of the acquisition
        threading.Thread.__init__(self)
        self._logger = logging.getLogger(self.__class__.__name__)
        self._acq_settings = deepcopy(acq_settings)
        self._acq_gui = acq_gui
        self._acq_directory = acq_directory
        self._abort_flag = abort_flag
        self._adv_settings = self._acq_settings.adv_settings

    def run(self):
        try:
            self._acq_gui.status_update("Initializing Acquisition")
            self._init_mm()
            self._init_hardware()
            self._write_acquisition_notes(self._acq_directory.root)
            self._abort_flag.abort = False
            self._get_acq_sequence().run()
        except exceptions.AbortAcquisitionException:
            self._abort_acquisition()
        except:
            self._logger.exception("exception raised during acquisition")
            self._abort_acquisition()
        else:
            self._reset_hardware()
            studio.app().refresh_gui()
            self._acq_gui.status_update("Your acquisition was successful!")

    def _abort_acquisition(self):
        self._acq_gui.status_update("Aborting Acquisition")
        self._reset_hardware()
        self._acq_gui.status_update("Aborted Acquisition" if self._abort_flag.abort else "Acquisition Failed. Check Logs.")

    def _get_acq_sequence(self):
        sequences = {AcqOrder.TIME_SAMP: TimeSampAcquisition,
                     AcqOrder.SAMP_TIME: SampTimeAcquisition,
                     AcqOrder.POS_TIME: PosTimeAcquisition}
        return sequences[self._adv_settings.acq_order](self._acq_settings, self._acq_gui, self._acq_directory, self._abort_flag)
        
    def _init_hardware(self):
        self._init_galvo()
        self._init_plc()

    def _init_galvo(self):
        if Galvo:
            Galvo.set_dslm_mode()

    def _init_plc(self):
        interval_ms = (self._acq_settings.get_first_step_size()/self._adv_settings.z_stack_stage_speed)*constants.S_TO_MS
        Plc.set_to_external_trigger_pulse_mode(interval_ms)

    def _reset_hardware(self):
        #set PLC to pulse continuously to send signal to camera in case it's frozen
        #in external trigger mode.
        Plc.set_to_continuous_pulse_mode(constants.CAMERA_RECOVERY_PULSE_INTERVAL_MS)
        core.stop_sequence_acquisition()
        Camera.set_exposure(Camera.DEFAULT_EXPOSURE)
        Camera.set_burst_mode()
        Plc.init_pulse_mode()
        core.clear_circular_buffer()
        #joystick sometimes does weird thing after SCAN module is sent
        Stage.reset_joystick()

    
class HTLSAcquisition(Acquisition, HardwareAcquisition):
    def __init__(self, 
                 htls_settings: HTLSSettings, 
                 acq_gui: HTLSAcqGui, 
                 acq_directory: AcqDirectory,
                 abort_flag: exceptions.AbortFlag):
        threading.Thread.__init__(self)
        #Reason for this deepcopy is so if settings are changed in the GUI while an acquisition is running,
        #it won't change the settings in the middle of the acquisition
        self._logger = logging.getLogger(self.__class__.__name__)
        self._htls_settings = htls_settings
        self._acq_gui = acq_gui
        self._acq_directory = acq_directory
        self._abort_flag = abort_flag
        self._acq_settings = self._htls_settings.acq_settings
        self._adv_settings = self._acq_settings.adv_settings
        
    def run(self):
        try:
            self._acq_gui.status_update("Initializing Acquisition")
            self._init_mm()
            self._init_hardware()
            self._abort_flag.abort = False
            sequence = HTLSSequence(self._htls_settings, self._acq_gui, self._acq_directory, self._abort_flag)
            sequence.run()
        except exceptions.AbortAcquisitionException:
            self._abort_acquisition()
        except:
            self._logger.exception("exception raised during acquisition")
            self._abort_acquisition()
        else:
            self._reset_hardware()
            studio.app().refresh_gui()
            self._acq_gui.status_update("Your acquisition was successful!")
        finally:
            self._write_acquisition_notes(self._acq_directory.root)

    def _abort_acquisition(self):
        self._acq_gui.status_update("Aborting Acquisition")
        self._reset_hardware()
        self._acq_gui.status_update("Aborted Acquisition" if self._abort_flag.abort else "Acquisition Failed. Check Logs.")

    def _init_hardware(self):
        self._init_galvo()
        self._init_plc()

    def _init_galvo(self):
        if Galvo:
            Galvo.set_dslm_mode()

    def _init_plc(self):
        interval_ms = self._htls_settings.fish_settings.region_list[0].z_stack_step_size/self._adv_settings.z_stack_stage_speed*constants.S_TO_MS
        Plc.set_to_external_trigger_pulse_mode(interval_ms)

    def _reset_hardware(self):
        Pump.terminate()
        #set PLC to pulse continuously to send signal to camera in case it's frozen
        #in external trigger mode.
        Plc.set_to_continuous_pulse_mode(constants.CAMERA_RECOVERY_PULSE_INTERVAL_MS)
        core.stop_sequence_acquisition()
        Camera.set_exposure(Camera.DEFAULT_EXPOSURE)
        Camera.set_burst_mode()
        Plc.init_pulse_mode()
        core.clear_circular_buffer()
        Stage.reset_joystick()
