import contextlib
from microscope_select.microscope_select import microscope, MicroscopeConfig
from utils import exceptions

if microscope == MicroscopeConfig.KLAMATH:
    from microscope_configs.klamath.models.galvo.galvo_settings import KlaGalvoSettings
    galvo_settings = KlaGalvoSettings()

    from microscope_configs.klamath.hardware.galvo import KlaGalvo
    galvo = KlaGalvo

if microscope == MicroscopeConfig.WILLAMETTE:
    from microscope_configs.willamette.hardware.camera import PcoEdge
    camera = PcoEdge()
elif microscope == MicroscopeConfig.KLAMATH:
    from microscope_configs.klamath.hardware.camera import Hamamatsu
    camera = Hamamatsu()

if microscope == MicroscopeConfig.WILLAMETTE:
    from microscope_configs.willamette.hardware.plc import WilPlc
    plc = WilPlc()
elif microscope == MicroscopeConfig.KLAMATH:
    from microscope_configs.klamath.hardware.plc import KlaPlc
    plc = KlaPlc()

if microscope == MicroscopeConfig.WILLAMETTE:
    from microscope_configs.willamette.hardware.stage import WilStage
    stage = WilStage()
elif microscope == MicroscopeConfig.KLAMATH:
    from microscope_configs.klamath.hardware.stage import KlaStage
    stage = KlaStage()

#Initializes plc to default state.
with contextlib.suppress(exceptions.GeneralHardwareException):
    camera.set_burst_mode()

#Initialize stage to default state.
with contextlib.suppress(exceptions.GeneralHardwareException):
    stage.set_x_stage_speed(stage._DEFAULT_STAGE_SPEED_UM_PER_S)
    stage.set_y_stage_speed(stage._DEFAULT_STAGE_SPEED_UM_PER_S)
    stage.set_z_stage_speed(stage._DEFAULT_STAGE_SPEED_UM_PER_S)
    stage.reset_joystick()

#Initializes plc to default state.
with contextlib.suppress(exceptions.GeneralHardwareException):
    plc.init_pulse_mode()
