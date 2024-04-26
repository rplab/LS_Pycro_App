import configparser
import os
import sys
from enum import Enum

from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication

from LS_Pycro_App.views import MicroscopeSelectDialog


MICROSCOPE_CONFIG_FILE_NAME = "microscope.cfg"
MICROSCOPE_CONFIG_SECTION = "Microscope Config"
MICROSCOPE_CONFIG_OPTION = "microscope config"

class MicroscopeConfig(Enum):
    KLAMATH = 1
    WILLAMETTE = 2
    HTLS = 3

microscope_config = configparser.ConfigParser()
microscope_config.read(MICROSCOPE_CONFIG_FILE_NAME)

def get_microscope_from_config():
    if configparser.ConfigParser().has_section(MICROSCOPE_CONFIG_SECTION):
        return MicroscopeConfig[microscope_config.get(MICROSCOPE_CONFIG_SECTION, MICROSCOPE_CONFIG_OPTION)]
    else:
        return MicroscopeConfig.WILLAMETTE

def write_microscope_to_config():
    if not microscope_config.has_section(MICROSCOPE_CONFIG_SECTION):
        microscope_config.add_section(MICROSCOPE_CONFIG_SECTION)
    microscope_config.set(MICROSCOPE_CONFIG_SECTION, MICROSCOPE_CONFIG_OPTION, microscope.name)

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
    with open(MICROSCOPE_CONFIG_FILE_NAME, "w") as configfile:
        microscope_config.write(configfile)
    return selected