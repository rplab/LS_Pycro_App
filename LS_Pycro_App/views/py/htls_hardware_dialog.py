# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\Raghu\Desktop\Microscope Software\LS_Pycro_App\LS_Pycro_App\views\ui\HTLSHardwareDialog.ui'
#
# Created by: PyQt5 UI code generator 5.15.10
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_HTLSHardwareDialog(object):
    def setupUi(self, HTLSHardwareDialog):
        HTLSHardwareDialog.setObjectName("HTLSHardwareDialog")
        HTLSHardwareDialog.resize(453, 199)
        self.gridLayout = QtWidgets.QGridLayout(HTLSHardwareDialog)
        self.gridLayout.setObjectName("gridLayout")
        self.stop_button = QtWidgets.QPushButton(HTLSHardwareDialog)
        self.stop_button.setObjectName("stop_button")
        self.gridLayout.addWidget(self.stop_button, 3, 2, 1, 1)
        self.rotation_label = QtWidgets.QLabel(HTLSHardwareDialog)
        self.rotation_label.setAlignment(QtCore.Qt.AlignCenter)
        self.rotation_label.setObjectName("rotation_label")
        self.gridLayout.addWidget(self.rotation_label, 0, 4, 1, 1)
        self.one_step_f_button = QtWidgets.QPushButton(HTLSHardwareDialog)
        self.one_step_f_button.setObjectName("one_step_f_button")
        self.gridLayout.addWidget(self.one_step_f_button, 1, 4, 1, 1)
        self.one_step_b_button = QtWidgets.QPushButton(HTLSHardwareDialog)
        self.one_step_b_button.setObjectName("one_step_b_button")
        self.gridLayout.addWidget(self.one_step_b_button, 2, 4, 1, 1)
        self.steps_label = QtWidgets.QLabel(HTLSHardwareDialog)
        self.steps_label.setObjectName("steps_label")
        self.gridLayout.addWidget(self.steps_label, 6, 3, 1, 1)
        self.steps_line_edit = QtWidgets.QLineEdit(HTLSHardwareDialog)
        self.steps_line_edit.setObjectName("steps_line_edit")
        self.gridLayout.addWidget(self.steps_line_edit, 6, 4, 1, 1)
        self.f_button = QtWidgets.QPushButton(HTLSHardwareDialog)
        self.f_button.setObjectName("f_button")
        self.gridLayout.addWidget(self.f_button, 3, 4, 1, 1)
        self.port_label = QtWidgets.QLabel(HTLSHardwareDialog)
        self.port_label.setObjectName("port_label")
        self.gridLayout.addWidget(self.port_label, 6, 1, 1, 1)
        self.port_combo_box = QtWidgets.QComboBox(HTLSHardwareDialog)
        self.port_combo_box.setObjectName("port_combo_box")
        self.gridLayout.addWidget(self.port_combo_box, 6, 2, 1, 1)
        self.velocity_label = QtWidgets.QLabel(HTLSHardwareDialog)
        self.velocity_label.setObjectName("velocity_label")
        self.gridLayout.addWidget(self.velocity_label, 1, 1, 1, 1)
        self.velocity_line_edit = QtWidgets.QLineEdit(HTLSHardwareDialog)
        self.velocity_line_edit.setObjectName("velocity_line_edit")
        self.gridLayout.addWidget(self.velocity_line_edit, 1, 2, 1, 1)
        self.max_button = QtWidgets.QPushButton(HTLSHardwareDialog)
        self.max_button.setObjectName("max_button")
        self.gridLayout.addWidget(self.max_button, 2, 2, 1, 1)
        self.pump_label = QtWidgets.QLabel(HTLSHardwareDialog)
        self.pump_label.setAlignment(QtCore.Qt.AlignCenter)
        self.pump_label.setObjectName("pump_label")
        self.gridLayout.addWidget(self.pump_label, 0, 2, 1, 1)
        self.zero_button = QtWidgets.QPushButton(HTLSHardwareDialog)
        self.zero_button.setObjectName("zero_button")
        self.gridLayout.addWidget(self.zero_button, 4, 2, 1, 1)
        self.b_button = QtWidgets.QPushButton(HTLSHardwareDialog)
        self.b_button.setObjectName("b_button")
        self.gridLayout.addWidget(self.b_button, 4, 4, 1, 1)
        self.toggle_valve_button = QtWidgets.QPushButton(HTLSHardwareDialog)
        self.toggle_valve_button.setObjectName("toggle_valve_button")
        self.gridLayout.addWidget(self.toggle_valve_button, 1, 0, 1, 1)
        self.valves_label = QtWidgets.QLabel(HTLSHardwareDialog)
        self.valves_label.setAlignment(QtCore.Qt.AlignCenter)
        self.valves_label.setObjectName("valves_label")
        self.gridLayout.addWidget(self.valves_label, 0, 0, 1, 1)

        self.retranslateUi(HTLSHardwareDialog)
        QtCore.QMetaObject.connectSlotsByName(HTLSHardwareDialog)

    def retranslateUi(self, HTLSHardwareDialog):
        _translate = QtCore.QCoreApplication.translate
        HTLSHardwareDialog.setWindowTitle(_translate("HTLSHardwareDialog", "Dialog"))
        self.stop_button.setText(_translate("HTLSHardwareDialog", "Stop"))
        self.rotation_label.setText(_translate("HTLSHardwareDialog", "Rotation"))
        self.one_step_f_button.setText(_translate("HTLSHardwareDialog", "One Step Forward"))
        self.one_step_b_button.setText(_translate("HTLSHardwareDialog", "One Step Backward"))
        self.steps_label.setText(_translate("HTLSHardwareDialog", "Steps"))
        self.f_button.setText(_translate("HTLSHardwareDialog", "Forward"))
        self.port_label.setText(_translate("HTLSHardwareDialog", "Port"))
        self.velocity_label.setText(_translate("HTLSHardwareDialog", "Velocity"))
        self.max_button.setText(_translate("HTLSHardwareDialog", "Max"))
        self.pump_label.setText(_translate("HTLSHardwareDialog", "Pump"))
        self.zero_button.setText(_translate("HTLSHardwareDialog", "Zero"))
        self.b_button.setText(_translate("HTLSHardwareDialog", "Backward"))
        self.toggle_valve_button.setText(_translate("HTLSHardwareDialog", "Open"))
        self.valves_label.setText(_translate("HTLSHardwareDialog", "Valves"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    HTLSHardwareDialog = QtWidgets.QDialog()
    ui = Ui_HTLSHardwareDialog()
    ui.setupUi(HTLSHardwareDialog)
    HTLSHardwareDialog.show()
    sys.exit(app.exec_())
