from microscope_configs.klamath.hardware.camera import Camera
from models.acquisition.adv_settings import AdvSettings
from utils import constants, general_functions

class AdvSettings(AdvSettings):
    def __init__(self):
        super().__init__()
        self.lsrm_enabled: bool = False
        self.edge_trigger_enabled: bool = False
        self.speed_list: list[int] = [15, 30, 45]
        self.z_stack_exposure: float = general_functions.framerate_to_exposure(self.z_stack_stage_speed)
    
    @property
    def edge_trigger_enabled(self):
        return self._edge_trigger_enabled

    @edge_trigger_enabled.setter
    def edge_trigger_enabled(self, value):
        self._edge_trigger_enabled = value
        if hasattr(self, "_z_stack_exposure"):
            self.z_stack_exposure = self.z_stack_exposure

    @property
    def z_stack_exposure(self):
        return self._z_stack_exposure

    @z_stack_exposure.setter
    def z_stack_exposure(self, value):
        if not self.spectral_z_stack_enabled:
            if not self.edge_trigger_enabled:
                self._z_stack_exposure = round(1/(self.z_stack_stage_speed*constants.UM_TO_MM), 3)
            else:
                max_exposure = Camera.get_max_edge_trigger_exposure(self.z_stack_stage_speed)
                self._z_stack_exposure = round(general_functions.value_in_range(value, Camera.MIN_EXPOSURE, max_exposure), 3)
        else:
            self._z_stack_exposure = max(value, Camera.MIN_EXPOSURE)