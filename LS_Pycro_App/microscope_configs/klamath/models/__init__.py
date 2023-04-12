from microscope_select.microscope_select import microscope, MicroscopeConfig

if microscope == MicroscopeConfig.KLAMATH:
    from microscope_configs.klamath.models.galvo.galvo_settings import GalvoSettings
    galvo_settings = GalvoSettings()