from acquisition.acquisition import Acquisition
from microscope_configs.klamath.hardware.galvo import Galvo
from models import galvo_settings

class Acquisition(Acquisition):
    def _init_additional_hardware(self):
        """
        initialize hardware that isn't the camera, plc, or stage.
        """
        Galvo.set_dslm_mode()

    def _write_settings_to_config(self): 
        galvo_settings.write_to_config()
        self._acq_settings.write_to_config()
