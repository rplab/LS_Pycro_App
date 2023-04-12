import sys
from controllers.acq_controller import AcqController

class AcqController(AcqController):
    def __init__(self):
        super().__init__()
        # Initialize AdvancedSettingsDialog event handlers
        self._adv_settings_dialog.custom_exposure_check_box.clicked.connect(self._custom_exposure_check_clicked)
        self._adv_settings_dialog.lsrm_check_box.clicked.connect(self._lsrm_check_clicked)

    def _custom_exposure_check_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._adv_settings.edge_trigger_enabled = self._adv_settings_dialog.custom_exposure_check_box.isChecked()

        self._refresh_dialogs()

    def _lsrm_check_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._adv_settings.lsrm_enabled = self._adv_settings_dialog.lsrm_check_box.isChecked()

        self._refresh_dialogs()

    def _refresh_adv_settings_dialog(self):
        super()._refresh_adv_settings_dialog()
        self._adv_settings_dialog.custom_exposure_check_box.setChecked(self._adv_settings.edge_trigger_enabled)
        self._adv_settings_dialog.lsrm_check_box.setChecked(self._adv_settings.lsrm_enabled)