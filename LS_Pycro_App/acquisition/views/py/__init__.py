from PyQt5 import QtWidgets
from LS_Pycro_App.microscope_select.microscope_select import microscope, MicroscopeConfig
from LS_Pycro_App.acquisition.views.py.abort_dialog import Ui_AbortDialog
from LS_Pycro_App.acquisition.views.py.acq_dialog import Ui_AcqDialog
from LS_Pycro_App.acquisition.views.py.acq_order_dialog import Ui_AcqOrderDialog
from LS_Pycro_App.acquisition.views.py.acq_regions_dialog import Ui_AcqRegionsDialog
from LS_Pycro_App.acquisition.views.py.acq_settings_dialog import Ui_AcqSettingsDialog

if microscope == MicroscopeConfig.WILLAMETTE:
    from LS_Pycro_App.acquisition.views.py.adv_settings_dialog import Wil_Ui_AdvSettingsDialog as Ui_AdvSettingsDialog
elif microscope == MicroscopeConfig.KLAMATH:
    from LS_Pycro_App.acquisition.views.py.adv_settings_dialog import Kla_Ui_AdvSettingsDialog as Ui_AdvSettingsDialog


class AbortDialog(Ui_AbortDialog, QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


class AcqDialog(Ui_AcqDialog, QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


class AcqOrderDialog(Ui_AcqOrderDialog, QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


class AcqRegionsDialog(Ui_AcqRegionsDialog, QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


class AcqSettingsDialog(Ui_AcqSettingsDialog, QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


class AdvSettingsDialog(Ui_AdvSettingsDialog, QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


class BrowseDialog(QtWidgets.QFileDialog):
    def __init__(self):
        super().__init__()    