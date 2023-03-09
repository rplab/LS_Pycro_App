import sys
from PyQt5.QtWidgets import QApplication
from microscope_select.microscope_select import select_microscope

#__init__ files are run when a package is import for the first time. Thus, we first select the microscope,
#then the __init__ files select the correct modules to use in their respective namespaces, and then the 
#main application runs.
microscope_was_selected = select_microscope()

if microscope_was_selected:
    from controllers import MainController
    app = QApplication(sys.argv)
    controller = MainController()
    app.exec_()
