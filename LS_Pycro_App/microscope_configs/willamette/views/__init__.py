from PyQt5 import QtWidgets
from microscope_configs.willamette.views.py.adv_settings_dialog import Ui_AdvSettingsDialog
from microscope_configs.willamette.views.py.main_window import Ui_MainWindow

class AdvSettingsDialog(QtWidgets.QDialog, Ui_AdvSettingsDialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)