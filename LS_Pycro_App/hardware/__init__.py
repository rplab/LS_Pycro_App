import contextlib
from microscope_select.microscope_select import microscope, MicroscopeConfig
from utils import exceptions

if microscope == MicroscopeConfig.KLAMATH:
    from microscope_configs.klamath.hardware.galvo import Galvo

if microscope == MicroscopeConfig.WILLAMETTE:
    from microscope_configs.willamette.hardware.camera import Camera
elif microscope == MicroscopeConfig.KLAMATH:
    from microscope_configs.klamath.hardware.camera import Camera

if microscope == MicroscopeConfig.WILLAMETTE:
    from microscope_configs.willamette.hardware.plc import Plc
elif microscope == MicroscopeConfig.KLAMATH:
    from microscope_configs.klamath.hardware.plc import Plc

if microscope == MicroscopeConfig.WILLAMETTE:
    from microscope_configs.willamette.hardware.stage import Stage
elif microscope == MicroscopeConfig.KLAMATH:
    from microscope_configs.klamath.hardware.stage import Stage

#Initializes plc to default state.
with contextlib.suppress(exceptions.GeneralHardwareException):
    Camera.set_burst_mode()

#Initialize stage to default state.
with contextlib.suppress(exceptions.GeneralHardwareException):
    Stage.set_x_stage_speed(Stage._DEFAULT_STAGE_SPEED_UM_PER_S)
    Stage.set_y_stage_speed(Stage._DEFAULT_STAGE_SPEED_UM_PER_S)
    Stage.set_z_stage_speed(Stage._DEFAULT_STAGE_SPEED_UM_PER_S)
    Stage.reset_joystick()

#Initializes plc to default state.
with contextlib.suppress(exceptions.GeneralHardwareException):
    Plc.init_pulse_mode()
