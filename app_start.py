import sys

from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication

from LS_Pycro_App.microscope_select.microscope_select import select_microscope

#__init__ files are run when a package is import for the first time. Thus, we first select the microscope,
#then the __init__ files select the correct modules to use in their respective namespaces, and then the 
#main application runs.
microscope_was_selected = select_microscope()

def set_icon(app: QApplication, controller):
    app.setWindowIcon(QtGui.QIcon('app_icon.png'))
    controller._main_window.setWindowIcon(QtGui.QIcon('app_icon.png'))

if microscope_was_selected:
    from LS_Pycro_App.main.main_controller import MainController
    app = QApplication(sys.argv)
    controller = MainController()
    set_icon(app, controller)
    app.exec_()
