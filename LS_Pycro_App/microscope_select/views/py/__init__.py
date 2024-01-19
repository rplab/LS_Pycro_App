from PyQt5 import QtWidgets

from LS_Pycro_App.microscope_select.views.py.microscope_select_dialog import Ui_MicroscopeSelectDialog


class MicroscopeSelectDialog(Ui_MicroscopeSelectDialog, QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)