from PyQt5 import QtWidgets
from LS_Pycro_App.hardware.galvo.views.galvo_dialog import Ui_GalvoDialog


class GalvoDialog(Ui_GalvoDialog, QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
