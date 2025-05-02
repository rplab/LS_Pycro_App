import logging

from LS_Pycro_App.hardware import Plc, Camera, Galvo
from LS_Pycro_App.hardware.camera import Hamamatsu
from LS_Pycro_App.utils import constants, general_functions

logger = logging.getLogger(__name__)

def set_continuous_lsrm(framerate):
    if Galvo and Camera is Hamamatsu:
        Galvo.settings.lsrm_framerate = min(framerate, Camera.LSRM_MAX_FRAMERATE)
        Galvo.set_lsrm_mode()
        Plc.set_to_continuous_pulse_mode(1/framerate)
        Camera.set_lsrm_mode(Galvo.settings.lsrm_ili, Galvo.settings.lsrm_num_lines)
    else:
        message = "Cannot set system to continuous lsrm."
        if not Galvo:
            logger.warning(f"{message} Galvo is None.")
        if not (Camera is Hamamatsu):
            logger.warning(f"{message} Galvo is not Hamamatsu.")

def set_triggered_lsrm(exposure, pulse_interval_ms):
    if Galvo and Plc and (Camera is Hamamatsu):
        framerate = general_functions.exposure_to_frequency(exposure)
        Galvo.settings.lsrm_framerate = min(framerate, Camera.LSRM_MAX_FRAMERATE)
        if pulse_interval_ms*constants.MS_TO_S > 1/Camera.LSRM_MAX_FRAMERATE:
            raise ValueError("pulse interval is too short for LSRM")
        Galvo.set_lsrm_mode()
        Plc.set_to_external_trigger_mode(pulse_interval_ms)
        Camera.set_lsrm_mode(Galvo.settings.lsrm_ili, Galvo.settings.lsrm_num_lines)
    else:
        message = "Cannot set system to continuous lsrm."
        if not Galvo:
            logger.warning(f"{message} Galvo is None.")
        if not (Camera is Hamamatsu):
            logger.warning(f"{message} Galvo is not Hamamatsu.")
