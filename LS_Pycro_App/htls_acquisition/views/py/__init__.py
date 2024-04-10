from PyQt5 import QtWidgets


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
   