from PyQt5 import QtWidgets

from LS_Pycro_App.views.py.abort_dialog import Ui_AbortDialog
from LS_Pycro_App.views.py.acq_dialog import Ui_AcqDialog
from LS_Pycro_App.views.py.acq_order_dialog import Ui_AcqOrderDialog
from LS_Pycro_App.views.py.acq_regions_dialog import Ui_AcqRegionsDialog
from LS_Pycro_App.views.py.acq_settings_dialog import Ui_AcqSettingsDialog
from LS_Pycro_App.views.py.adv_settings_dialog import Ui_AdvSettingsDialog
from LS_Pycro_App.views.py.galvo_dialog import Ui_GalvoDialog
from LS_Pycro_App.views.py.htls_acq_dialog import Ui_HTLSAcqDialog
from LS_Pycro_App.views.py.htls_acq_regions_dialog import Ui_HTLSAcqRegionsDialog
from LS_Pycro_App.views.py.htls_acq_settings_dialog import Ui_HTLSAcqSettingsDialog
from LS_Pycro_App.views.py.htls_adv_settings_dialog import Ui_HTLSAdvSettingsDialog
from LS_Pycro_App.views.py.htls_main_window import Ui_HTLSMainWindow
from LS_Pycro_App.views.py.kla_main_window import Ui_KlaMainWindow
from LS_Pycro_App.views.py.microscope_select_dialog import Ui_MicroscopeSelectDialog
from LS_Pycro_App.views.py.pump_and_rotation_dialog import Ui_PumpAndRotationDialog
from LS_Pycro_App.views.py.wil_main_window import Ui_WilMainWindow


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


class GalvoDialog(Ui_GalvoDialog, QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


class HTLSAcqDialog(Ui_HTLSAcqDialog, QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


class HTLSAcqSettingsDialog(Ui_HTLSAcqSettingsDialog, QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


class HTLSAcqRegionsDialog(Ui_HTLSAcqRegionsDialog, QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


class HTLSAdvSettingsDialog(Ui_HTLSAdvSettingsDialog, QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


class HTLSMainWindow(Ui_HTLSMainWindow, QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


class KlaMainWindow(Ui_KlaMainWindow, QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


class MicroscopeSelectDialog(Ui_MicroscopeSelectDialog, QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


class PumpAndRotationDialog(Ui_PumpAndRotationDialog, QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


class WilMainWindow(Ui_WilMainWindow, QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
