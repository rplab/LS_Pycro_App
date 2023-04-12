"""
Notes:

-Order of imports matters! If there are import errors, it's almost 100% because of a circular dependency.
"""
from microscope_select.microscope_select import microscope, MicroscopeConfig

if microscope == MicroscopeConfig.KLAMATH:
    from microscope_configs.klamath.models.galvo.galvo_settings import GalvoSettings
    galvo_settings = GalvoSettings()
    galvo_settings.init_from_config()
    
if microscope == MicroscopeConfig.WILLAMETTE:
    from microscope_configs.willamette.models.acquisition.adv_settings import AdvSettings
elif microscope == MicroscopeConfig.KLAMATH:
    from microscope_configs.klamath.models.acquisition.adv_settings import AdvSettings
