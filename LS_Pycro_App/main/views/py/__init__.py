from PyQt5 import QtWidgets
from LS_Pycro_App.main.microscope_select.microscope_select import microscope, MicroscopeConfig

if microscope == MicroscopeConfig.WILLAMETTE:
    from LS_Pycro_App.main.views.py.main_window import Wil_Ui_MainWindow as Ui_MainWindow
elif microscope == MicroscopeConfig.KLAMATH:
    from LS_Pycro_App.main.views.py.main_window import Kla_Ui_MainWindow as Ui_MainWindow


class MainWindow(Ui_MainWindow, QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)