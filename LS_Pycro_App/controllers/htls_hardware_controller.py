import logging
import sys

from PyQt5 import QtGui

from LS_Pycro_App.hardware import Pump, Rotation, Valves
from LS_Pycro_App.hardware.pump import Port
from LS_Pycro_App.views import HTLSHardwareDialog

class HTLSHardwareController():
    VALVE_OPEN_TEXT = "Open"
    VALVE_CLOSE_TEXT = "Close"

    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._dialog = HTLSHardwareDialog()

        self._dialog.toggle_valve_button.clicked.connect(self._toggle_valve_button_clicked)
        self._dialog.velocity_line_edit.textEdited.connect(self.velocity_line_edit_event)
        self._dialog.max_button.clicked.connect(self._max_button_clicked)
        self._dialog.stop_button.clicked.connect(self._stop_button_clicked)
        self._dialog.zero_button.clicked.connect(self._zero_button_clicked)
        self._dialog.port_combo_box.activated.connect(self._port_combo_box_clicked)
        self._dialog.one_step_f_button.clicked.connect(self._one_step_f_button_clicked)
        self._dialog.one_step_b_button.clicked.connect(self._one_step_b_button_clicked)
        self._dialog.f_button.clicked.connect(self._f_button_clicked)
        self._dialog.b_button.clicked.connect(self._b_button_clicked)
        
        self._dialog.toggle_valve_button.setText(HTLSHardwareController.VALVE_CLOSE_TEXT if Valves.are_open else HTLSHardwareController.VALVE_CLOSE_TEXT)
        self._dialog.velocity_line_edit.setText(str(Pump.velocity))
        self._dialog.steps_line_edit.setText(str(70))

        for p in Port:
            self._dialog.port_combo_box.addItem(p.name)

        validator = QtGui.QIntValidator()
        validator.setBottom(0)
        

    def _toggle_valve_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        if Valves.are_open:
            Valves.close()
            self._dialog.toggle_valve_button.setText("Open")
        else:
            Valves.open()
            self._dialog.toggle_valve_button.setText("Close")

    def velocity_line_edit_event(self, text):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        Pump.set_velocity(int(text))

    def _max_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        Pump.set_max()
    
    def _stop_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        Pump.terminate()

    def _zero_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        Pump.set_zero()

    def _port_combo_box_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        Pump.set_port(Port[self._dialog.port_combo_box.currentText()])

    def _one_step_f_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        Rotation.move_forward(1)

    def _one_step_b_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        Rotation.move_backward(1)

    def _f_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        Rotation.move_forward(int(self._dialog.steps_line_edit.text()))

    def _b_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        Rotation.move_backward(int(self._dialog.steps_line_edit.text()))
        