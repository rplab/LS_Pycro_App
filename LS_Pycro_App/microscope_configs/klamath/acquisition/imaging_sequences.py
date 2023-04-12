from acquisition.imaging_sequences import Snap, Video, SpectralVideo, ZStack, SpectralZStack
from microscope_configs.klamath.hardware.camera import Camera
from microscope_configs.klamath.hardware.galvo import Galvo
from models import galvo_settings
from utils import general_functions
from utils.pycro import core

class Snap(Snap):
    def _pre_acquire_hardware_init(self):
        if self._adv_settings.lsrm_enabled:
            framerate = general_functions.exposure_to_framerate(self._region.snap_exposure)
            galvo_settings.lsrm_framerate = min(framerate, Camera.LSRM_MAX_FRAMERATE)
            Galvo.set_lsrm_mode()
            Camera.set_lsrm_mode(galvo_settings.lsrm_ili, galvo_settings.lsrm_num_lines)
        else:
            core.set_exposure(self._region.snap_exposure)
            Camera.set_burst_mode()


class Video(Video):
    def _pre_acquire_hardware_init(self):
        if self._adv_settings.lsrm_enabled:
            framerate = general_functions.exposure_to_framerate(self._region.video_exposure)
            galvo_settings.lsrm_framerate = min(framerate, Camera.LSRM_MAX_FRAMERATE)
            Galvo.set_lsrm_mode()
            Camera.set_lsrm_mode(galvo_settings.lsrm_ili, galvo_settings.lsrm_num_lines)
        else:
            core.set_exposure(self._region.video_exposure)
            Camera.set_burst_mode()


class SpectralVideo(SpectralVideo):
    def _pre_acquire_hardware_init(self):
        if self._adv_settings.lsrm_enabled:
            framerate = general_functions.exposure_to_framerate(self._region.video_exposure)
            galvo_settings.lsrm_framerate = min(framerate, Camera.LSRM_MAX_FRAMERATE)
            Galvo.set_lsrm_mode()
            Camera.set_lsrm_mode(galvo_settings.lsrm_ili, galvo_settings.lsrm_num_lines)
        else:
            core.set_exposure(self._region.video_exposure)
            Camera.set_burst_mode()


class ZStack(ZStack):
    def _pre_acquire_hardware_init(self):
        if self._adv_settings.lsrm_enabled:
            framerate = self._adv_settings.z_stack_stage_speed
            #current available stage speeds are < max lsrm framerate. This is here just in case that isn't the case
            #in the future.
            galvo_settings.lsrm_framerate = min(framerate, Camera.LSRM_MAX_FRAMERATE)
            Galvo.set_lsrm_mode()
            Camera.set_lsrm_mode(galvo_settings.lsrm_ili, galvo_settings.lsrm_num_lines)
        else:
            if self._adv_settings.edge_trigger_enabled or self._region.z_stack_step_size > 1:
                Camera.set_edge_trigger_mode()
            else:
                Camera.set_sync_readout_mode()
            core.set_exposure(self._adv_settings.z_stack_exposure)


class SpectralZStack(SpectralZStack):
    def _pre_acquire_hardware_init(self):
        if self._adv_settings.lsrm_enabled:
            framerate = general_functions.exposure_to_framerate(self._adv_settings.z_stack_exposure)
            galvo_settings.lsrm_framerate = min(framerate, Camera.LSRM_MAX_FRAMERATE)
            Galvo.set_lsrm_mode()
            Camera.set_lsrm_mode(galvo_settings.lsrm_ili, galvo_settings.lsrm_num_lines)
        else:
            core.set_exposure(self._adv_settings.z_stack_exposure)
            Camera.set_burst_mode()

