from PyQt5 import QtWidgets
from LS_Pycro_App.acquisition.views.py.abort_dialog import Ui_AbortDialog
from LS_Pycro_App.acquisition.views.py.acq_dialog import Ui_AcqDialog
from LS_Pycro_App.acquisition.views.py.acq_order_dialog import Ui_AcqOrderDialog
from LS_Pycro_App.acquisition.views.py.acq_regions_dialog import Ui_AcqRegionsDialog
from LS_Pycro_App.acquisition.views.py.acq_settings_dialog import Ui_AcqSettingsDialog
from LS_Pycro_App.acquisition.views.py.adv_settings_dialog import Ui_AdvSettingsDialog


class AbortDialog(QtWidgets.QDialog, Ui_AbortDialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


class AcqDialog(QtWidgets.QDialog, Ui_AcqDialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


class AcqOrderDialog(QtWidgets.QDialog, Ui_AcqOrderDialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


class AcqRegionsDialog(QtWidgets.QDialog, Ui_AcqRegionsDialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


class AcqSettingsDialog(QtWidgets.QDialog, Ui_AcqSettingsDialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


class AdvSettingsDialog(QtWidgets.QDialog, Ui_AdvSettingsDialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


class BrowseDialog(QtWidgets.QFileDialog):
    def __init__(self):
        super().__init__()    