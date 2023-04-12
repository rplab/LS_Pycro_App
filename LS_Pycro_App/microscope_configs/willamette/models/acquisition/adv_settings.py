import numpy as np
from microscope_configs.willamette.hardware.camera import Camera
from models.acquisition.adv_settings import AdvSettings
from utils import constants, general_functions

class AdvSettings(AdvSettings):
    def __init__(self):
        super().__init__()
        self.z_stack_exposure: float = general_functions.z_stack_speed_to_exposure(self.z_stack_stage_speed)
    
    @property
    def z_stack_exposure(self):
        return self._z_stack_exposure
    
    @z_stack_exposure.setter
    def z_stack_exposure(self, value):
        #Maximum exp when performing continuous z-stack is floor(1/z_stack_speed) due to how the triggering works. 
        #This makes it so that if continuous z-stack is enabled and an exp time greater than this vaolue is entered, 
        #it is corrected.
        if not self.spectral_z_stack_enabled:
            max_exposure = np.floor(1/(self.z_stack_stage_speed*constants.UM_TO_MM))
            self._z_stack_exposure = round(general_functions.value_in_range(value, Camera.MIN_EXPOSURE, max_exposure), 3)
        else:
            self._z_stack_exposure = max(value, Camera.MIN_EXPOSURE)
