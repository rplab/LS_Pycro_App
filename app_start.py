import ctypes
import logging
import sys
import traceback

from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication

from LS_Pycro_App.controllers.select_controller import select_microscope


def _excepthook(exc_type, exc, tb):
    #PyQt5 aborts the whole app if an exception escapes a Qt slot (e.g. a button handler) and no
    #exception hook is installed. Log it instead (to the logs/ file) so the app keeps running.
    logging.getLogger("uncaught").error("Uncaught exception", exc_info=(exc_type, exc, tb))
    traceback.print_exception(exc_type, exc, tb)

sys.excepthook = _excepthook

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
