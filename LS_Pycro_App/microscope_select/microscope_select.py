import sys
from enum import Enum

from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication

from LS_Pycro_App.utils import user_config
from LS_Pycro_App.microscope_select.views.py import MicroscopeSelectDialog


CONFIG_SECTION = "Microscope Config"
CONFIG_OPTION = "microscope config"

class MicroscopeConfig(Enum):
    KLAMATH = 1
    WILLAMETTE = 2

def get_microscope_from_config():
    if user_config.has_section(CONFIG_SECTION):
        return MicroscopeConfig[user_config.get(CONFIG_SECTION, CONFIG_OPTION)]
    else:
        return MicroscopeConfig.WILLAMETTE

def write_microscope_to_config():
    if not user_config.has_section(CONFIG_SECTION):
        user_config.add_section(CONFIG_SECTION)
    user_config.set(CONFIG_SECTION, CONFIG_OPTION, microscope.name)

selected = False
microscope = get_microscope_from_config()
def select_microscope():
    global microscope, selected
    app = QApplication(sys.argv)
    microscope_dialog = MicroscopeSelectDialog()

    microscope_list_model = QtGui.QStandardItemModel()
    microscope_dialog.microscope_combo_box.setModel(microscope_list_model)
    for config in MicroscopeConfig:
        item = QtGui.QStandardItem(config.name)
        microscope_list_model.appendRow(item)
    default_index = microscope.value - 1
    microscope_dialog.microscope_combo_box.setCurrentIndex(default_index)

    def confirm_button_clicked():
        global microscope, selected
        microscope = MicroscopeConfig[microscope_dialog.microscope_combo_box.currentText()]
        selected = True
        write_microscope_to_config()
        app.exit()

    microscope_dialog.confirm_button.clicked.connect(confirm_button_clicked)
    microscope_dialog.show()
    app.exec_()
    return selected