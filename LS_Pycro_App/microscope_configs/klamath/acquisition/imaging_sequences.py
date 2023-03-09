from acquisition.imaging_sequences import Snap, Video, SpectralVideo, ZStack, SpectralZStack
from microscope_configs.klamath.hardware.camera import Hamamatsu
from utils.pycro import core

class Snap(Snap):
    def _pre_acquire_hardware_init(self):
        core.set_exposure(self._region.snap_exposure)
        Hamamatsu.set_burst_mode()


class Video(Video):
    def _pre_acquire_hardware_init(self):
        core.set_exposure(self._region.video_exposure)
        Hamamatsu.set_burst_mode()


class SpectralVideo(SpectralVideo):
    def _pre_acquire_hardware_init(self):
        core.set_exposure(self._region.video_exposure)
        Hamamatsu.set_burst_mode()


class ZStack(ZStack):
    def _pre_acquire_hardware_init(self):
        core.set_exposure(self._adv_settings.z_stack_exposure)
        Hamamatsu.set_ext_trig_mode()


class SpectralZStack(SpectralZStack):
    def _pre_acquire_hardware_init(self):
        core.set_exposure(self._adv_settings.z_stack_exposure)
        Hamamatsu.set_burst_mode()

