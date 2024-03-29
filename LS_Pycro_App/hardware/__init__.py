import contextlib
from LS_Pycro_App.microscope_select.microscope_select import microscope, MicroscopeConfig
from LS_Pycro_App.utils import exceptions

if microscope == MicroscopeConfig.WILLAMETTE:
    Galvo = None
    from LS_Pycro_App.hardware.camera import Pco as Camera
    from LS_Pycro_App.hardware.plc import WilPlc as Plc
    from LS_Pycro_App.hardware.stage import WilStage as Stage
elif microscope == MicroscopeConfig.KLAMATH:
    import LS_Pycro_App.hardware.galvo.galvo as Galvo
    from LS_Pycro_App.hardware.camera import Hamamatsu as Camera
    from LS_Pycro_App.hardware.plc import KlaPlc as Plc
    from LS_Pycro_App.hardware.stage import KlaStage as Stage

#Initializes camera to default state.
with contextlib.suppress(exceptions.HardwareException):
    Camera.set_burst_mode()

#Initialize stage to default state.
with contextlib.suppress(exceptions.HardwareException):
    Stage.init()

#Initializes plc to default state.
with contextlib.suppress(exceptions.HardwareException):
    Plc.init_pulse_mode()
