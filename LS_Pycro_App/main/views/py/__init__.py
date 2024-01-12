from PyQt5 import QtWidgets, QtCore
from LS_Pycro_App.microscope_select.microscope_select import microscope, MicroscopeConfig

if microscope == MicroscopeConfig.WILLAMETTE:
    from LS_Pycro_App.main.views.py.wil_main_window import Wil_Ui_MainWindow as Ui_MainWindow
else:
    from LS_Pycro_App.main.views.py.kla_main_window import Kla_Ui_MainWindow as Ui_MainWindow


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)