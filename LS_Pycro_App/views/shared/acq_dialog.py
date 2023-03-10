# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\Will LSM\Desktop\Microscope Software\LS_Pycro_App\LS_Pycro_App\views\ui_files\AcqDialog.ui'
#
# Created by: PyQt5 UI code generator 5.15.7
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_AcqDialog(object):
    def setupUi(self, AcqDialog):
        AcqDialog.setObjectName("AcqDialog")
        AcqDialog.resize(420, 176)
        self.fish_label = QtWidgets.QLabel(AcqDialog)
        self.fish_label.setGeometry(QtCore.QRect(186, 30, 61, 20))
        self.fish_label.setAlignment(QtCore.Qt.AlignCenter)
        self.fish_label.setObjectName("fish_label")
        self.region_label = QtWidgets.QLabel(AcqDialog)
        self.region_label.setGeometry(QtCore.QRect(180, 50, 71, 20))
        self.region_label.setAlignment(QtCore.Qt.AlignCenter)
        self.region_label.setObjectName("region_label")
        self.acq_label = QtWidgets.QLabel(AcqDialog)
        self.acq_label.setGeometry(QtCore.QRect(0, 60, 421, 71))
        font = QtGui.QFont()
        font.setPointSize(16)
        self.acq_label.setFont(font)
        self.acq_label.setAlignment(QtCore.Qt.AlignCenter)
        self.acq_label.setObjectName("acq_label")
        self.abort_button = QtWidgets.QPushButton(AcqDialog)
        self.abort_button.setGeometry(QtCore.QRect(180, 140, 75, 23))
        self.abort_button.setObjectName("abort_button")
        self.time_point_label = QtWidgets.QLabel(AcqDialog)
        self.time_point_label.setGeometry(QtCore.QRect(170, 10, 91, 16))
        self.time_point_label.setAlignment(QtCore.Qt.AlignCenter)
        self.time_point_label.setObjectName("time_point_label")

        self.retranslateUi(AcqDialog)
        QtCore.QMetaObject.connectSlotsByName(AcqDialog)

    def retranslateUi(self, AcqDialog):
        _translate = QtCore.QCoreApplication.translate
        AcqDialog.setWindowTitle(_translate("AcqDialog", "Acquisition"))
        self.fish_label.setText(_translate("AcqDialog", "Fish 1"))
        self.region_label.setText(_translate("AcqDialog", "Region 1"))
        self.acq_label.setText(_translate("AcqDialog", "No Acquisition Running"))
        self.abort_button.setWhatsThis(_translate("AcqDialog", "<html><head/><body><p>Opens up Abort Dialog to abort running acquisition</p></body></html>"))
        self.abort_button.setText(_translate("AcqDialog", "Abort"))
        self.time_point_label.setText(_translate("AcqDialog", "Time point 1"))
