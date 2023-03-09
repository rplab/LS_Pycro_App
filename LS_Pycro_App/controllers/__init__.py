from microscope_select.microscope_select import microscope, MicroscopeConfig


if microscope == MicroscopeConfig.WILLAMETTE:
    from microscope_configs.willamette.controllers.acq_controller import AcqController
elif microscope == MicroscopeConfig.KLAMATH:
    from microscope_configs.klamath.controllers.acq_controller import AcqController

if microscope == MicroscopeConfig.KLAMATH:
    from microscope_configs.klamath.controllers.galvo_controller import GalvoController

if microscope == MicroscopeConfig.WILLAMETTE:
    from microscope_configs.willamette.controllers.main_controller import MainController
elif microscope == MicroscopeConfig.KLAMATH:
    from microscope_configs.klamath.controllers.main_controller import MainController