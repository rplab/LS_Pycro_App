import ctypes
import sys

from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication

from LS_Pycro_App.controllers.select_controller import select_microscope

microscope_was_selected = select_microscope()

if microscope_was_selected:
    from LS_Pycro_App.controllers.main_controller import MainController
    app = QApplication(sys.argv)
    #This is what allows app icon to be used on taskbar
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("LS_Pycro_App")
    controller = MainController()
    app.setWindowIcon(QtGui.QIcon('app_icon.png'))
    controller._main_window.setWindowIcon(QtGui.QIcon('app_icon.png'))
    app.exec_()
