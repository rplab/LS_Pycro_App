from hardware import galvo_settings
from microscope_configs.klamath.hardware.camera import Hamamatsu
from models.acquisition.adv_settings import AdvSettings
from utils import constants, general_functions

class AdvSettings(AdvSettings):
    def __init__(self):
        super().__init__()
        self.lsrm_enabled: bool = False
        self.edge_trigger_enabled: bool = False
        self.speed_list: list[int] = [15, 30, 45, 60, 75]
        self.z_stack_stage_speed: int = 30
        self.z_stack_exposure: float = general_functions.z_stack_speed_to_exposure(self.z_stack_stage_speed)
    
    @property
    def z_stack_exposure(self):
        return self._z_stack_exposure
    
    @z_stack_exposure.setter
    def z_stack_exposure(self, value):
        if self.lsrm_enabled:
            self._z_stack_exposure = galvo_settings.lsrm_ili*galvo_settings.lsrm_num_lines
        elif not self.spectral_z_stack_enabled:
            if not self.edge_trigger_enabled:
                self._z_stack_exposure = round(1/(self.z_stack_stage_speed*constants.UM_TO_MM), 3)
            else:
                self._z_stack_exposure = round(min(Hamamatsu.get_max_edge_trigger_exposure(self.z_stack_stage_speed), value), 3)
        else:
            self._z_stack_exposure = value