import contextlib
from LS_Pycro_App.controllers.select_controller import microscope, MicroscopeConfig
from LS_Pycro_App.utils import exceptions

from LS_Pycro_App.hardware.plc import Plc
Galvo = None
Pump = None
Rotation = None
Valves = None
if microscope == MicroscopeConfig.WILLAMETTE:
    from LS_Pycro_App.hardware.camera import Pco as Camera
    from LS_Pycro_App.hardware.stage import WilStage as Stage
elif microscope == MicroscopeConfig.KLAMATH:
    import LS_Pycro_App.hardware.galvo as Galvo
    from LS_Pycro_App.hardware.camera import Hamamatsu as Camera
    from LS_Pycro_App.hardware.stage import KlaStage as Stage
elif microscope == MicroscopeConfig.HTLS:
    import LS_Pycro_App.hardware.galvo as Galvo
    import LS_Pycro_App.hardware.pump as Pump
    import LS_Pycro_App.hardware.rotation as Rotation
    import LS_Pycro_App.hardware.valves as Valves
    from LS_Pycro_App.hardware.camera import Hamamatsu as Camera
    from LS_Pycro_App.hardware.plc import Plc
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

if microscope == MicroscopeConfig.HTLS:
    with contextlib.suppress(exceptions.HardwareException):
        Pump.init()

    with contextlib.suppress(exceptions.HardwareException):
        Rotation.init()

    with contextlib.suppress(exceptions.HardwareException):
        Valves.init()
