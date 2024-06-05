"""
This file contains all the controller classes. There are currrently three: One to control all
other controllers, one to control image acquisitions, and one more to control the galvo mirrors.
Each controller has essentially one associated view (although the acquisition controller has multiple
windows).

Notes for future developers:

If there's one thing I want future developers to get out of this design, it's modularity. I hope it's obvious
that designing additional controllers, completely separate from the image acquisition package that I've made,
is the intended development route. 

I've spent an incredible amount of time on documentation and readability for two reasons:

1. It looks nice :)

2. I have no idea what the programming background of the next person to develop this will be. 

When I started this job, my coding background was not great and the code that was left behind was incomprehensible 
(both because I was inexperienced and because it was awful). I wanted to make something that (hopefully) someone with 
just a bit of knowledge of microscope automation and object-oriented programming could figure out. 

Future Changes:
- Probably should format everything to be in accordance with PEP 8. Currently using 120 line length limit, which I think is reasonable
with PyQt5. 80 seems like way too little.

- All the controllers are so boilerplatey. Not sure if there's an elegant way around this just due to how the PyQt5
API is. Will thing more about this.
"""

from PyQt5 import QtCore

from LS_Pycro_App.controllers.cls_controller import CLSController
from LS_Pycro_App.controllers.htls_controller import HTLSController
from LS_Pycro_App.controllers.galvo_controller import GalvoController
from LS_Pycro_App.controllers.htls_hardware_controller import HTLSHardwareController
from LS_Pycro_App.controllers.select_controller import microscope, MicroscopeConfig
from LS_Pycro_App.views import HTLSMainWindow, KlaMainWindow, WilMainWindow

class MainController(object):
    def __init__(self):
        #Same instances of studio, core, mm_hardware_commands, and spim_commands used throughout
        if microscope == MicroscopeConfig.KLAMATH:
            self._main_window = KlaMainWindow()
            self._acquisition_controller = CLSController()
            self._galvo_controller = GalvoController()
            self._main_window.galvo_button.clicked.connect(self._galvo_button_clicked)
        elif microscope == MicroscopeConfig.WILLAMETTE:
            self._main_window = WilMainWindow()
            self._acquisition_controller = CLSController()
        elif microscope == MicroscopeConfig.HTLS:
            self._main_window = HTLSMainWindow()
            self._acquisition_controller = HTLSController()
            self._galvo_controller = GalvoController()
            self._htls_hardware_controller = HTLSHardwareController()
            self._main_window.galvo_button.clicked.connect(self._galvo_button_clicked)
            self._main_window.rotation_and_pump_button.clicked.connect(self._rotation_and_pump_button_clicked)
        
        #initialize main window and event handlers.
        self._main_window.regions_button.clicked.connect(self._regions_button_clicked)
        self._main_window.exit_button.clicked.connect(self._exit_button_clicked)

        #This flag is set to disable thebuttons on the top right of the window.
        self._main_window.setWindowFlags(QtCore.Qt.WindowTitleHint)
        
        self._main_window.show()
    
    def _galvo_button_clicked(self):
        self._galvo_controller.galvo_dialog.show()
        self._galvo_controller.galvo_dialog.activateWindow()

    def _rotation_and_pump_button_clicked(self):
        self._htls_hardware_controller._dialog.show()
        self._htls_hardware_controller._dialog.activateWindow()

    def _regions_button_clicked(self):
        self._acquisition_controller.regions_dialog.show()
        self._acquisition_controller.regions_dialog.activateWindow()

    def _exit_button_clicked(self):
        quit()
