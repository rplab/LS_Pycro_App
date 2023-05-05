from acquisition.acquisition import Acquisition

class Acquisition(Acquisition):
    def _init_additional_hardware(self):
        """
        initialize hardware that isn't the camera, plc, or stage.
        """
        pass

    def _write_settings_to_config(self):
        self._acq_settings.write_to_config()
