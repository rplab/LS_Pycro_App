from PyQt5 import QtWidgets
from LS_Pycro_App.microscope_select.microscope_select import microscope, MicroscopeConfig

if microscope == MicroscopeConfig.WILLAMETTE:
    from LS_Pycro_App.main.views.py.wil_main_window import Ui_WilMainWindow as Ui_MainWindow
elif microscope == MicroscopeConfig.KLAMATH:
    from LS_Pycro_App.main.views.py.kla_main_window import Ui_KlaMainWindow as Ui_MainWindow


class MainWindow(Ui_MainWindow, QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)