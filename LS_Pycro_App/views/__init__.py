"""
This import scheme sucks ass but intellisense wasn't working by just importing views,
so for now this is the way.
"""
from microscope_select.microscope_select import microscope, MicroscopeConfig


if microscope == MicroscopeConfig.WILLAMETTE:
    from microscope_configs.willamette.views.wil_adv_settings_dialog import AdvSettingsDialog
elif microscope == MicroscopeConfig.KLAMATH:
    from microscope_configs.klamath.views.kla_adv_settings_dialog import AdvSettingsDialog


if microscope == MicroscopeConfig.WILLAMETTE:
    from microscope_configs.willamette.views.wil_main_window import MainWindow
elif microscope == MicroscopeConfig.KLAMATH:
    from microscope_configs.klamath.views.kla_main_window import MainWindow
