from PyQt5 import QtWidgets
from views.py.abort_dialog import Ui_AbortDialog
from views.py.acq_dialog import Ui_AcqDialog
from views.py.acq_order_dialog import Ui_AcqOrderDialog
from views.py.acq_regions_dialog import Ui_AcqRegionsDialog
from views.py.acq_settings_dialog import Ui_AcqSettingsDialog
from views.py.galvo_dialog import Ui_GalvoDialog

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


class GalvoDialog(QtWidgets.QDialog, Ui_GalvoDialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


class BrowseDialog(QtWidgets.QFileDialog):
    def __init__(self):
        super().__init__()