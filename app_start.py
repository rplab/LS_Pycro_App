import ctypes
import sys
from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication
from LS_Pycro_App.main.microscope_select.microscope_select import select_microscope

#__init__ files are run when a package is import for the first time. Thus, we first select the microscope,
#then the __init__ files select the correct modules to use in their respective namespaces, and then the 
#main application runs.
microscope_was_selected = select_microscope()

if microscope_was_selected:
    from LS_Pycro_App.main.main_controller import MainController
    app = QApplication(sys.argv)
    #app_id needed to override taskbar icon
    app_id = "LS_Pycro_App"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    controller = MainController()
    app.setWindowIcon(QtGui.QIcon('app_icon.png'))
    controller._main_window.setWindowIcon(QtGui.QIcon('app_icon.png'))
    app.exec_()
