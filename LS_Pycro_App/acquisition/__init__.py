from microscope_select.microscope_select import microscope, MicroscopeConfig

if microscope == MicroscopeConfig.WILLAMETTE:
    from microscope_configs.willamette.acquisition import imaging_sequences
elif microscope == MicroscopeConfig.KLAMATH:
    from microscope_configs.klamath.acquisition import imaging_sequences


if microscope == MicroscopeConfig.WILLAMETTE:
    from microscope_configs.willamette.acquisition.acquisition import Acquisition
elif microscope == MicroscopeConfig.KLAMATH:
    from microscope_configs.klamath.acquisition.acquisition import Acquisition