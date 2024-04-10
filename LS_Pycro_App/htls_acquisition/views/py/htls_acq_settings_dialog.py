# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\Raghu\Desktop\Microscope Software\LS_Pycro_App\LS_Pycro_App\htls_acquisition\views\ui\HTLSAcqSettingsDialog.ui'
#
# Created by: PyQt5 UI code generator 5.15.10
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_HTLSAcqSettingsDialog(object):
    def setupUi(self, HTLSAcqSettingsDialog):
        HTLSAcqSettingsDialog.setObjectName("HTLSAcqSettingsDialog")
        HTLSAcqSettingsDialog.resize(398, 392)
        self.channel_order_move_up_button = QtWidgets.QPushButton(HTLSAcqSettingsDialog)
        self.channel_order_move_up_button.setGeometry(QtCore.QRect(0, 110, 75, 23))
        self.channel_order_move_up_button.setObjectName("channel_order_move_up_button")
        self.channel_order_move_down_button = QtWidgets.QPushButton(HTLSAcqSettingsDialog)
        self.channel_order_move_down_button.setGeometry(QtCore.QRect(0, 150, 75, 23))
        self.channel_order_move_down_button.setObjectName("channel_order_move_down_button")
        self.channel_order_list_view = QtWidgets.QListView(HTLSAcqSettingsDialog)
        self.channel_order_list_view.setGeometry(QtCore.QRect(80, 90, 101, 101))
        self.channel_order_list_view.setObjectName("channel_order_list_view")
        self.channel_order_label = QtWidgets.QLabel(HTLSAcqSettingsDialog)
        self.channel_order_label.setGeometry(QtCore.QRect(40, 60, 101, 20))
        self.channel_order_label.setAlignment(QtCore.Qt.AlignCenter)
        self.channel_order_label.setObjectName("channel_order_label")
        self.browse_button = QtWidgets.QPushButton(HTLSAcqSettingsDialog)
        self.browse_button.setGeometry(QtCore.QRect(160, 240, 75, 23))
        self.browse_button.setObjectName("browse_button")
        self.save_path_line_edit = QtWidgets.QLineEdit(HTLSAcqSettingsDialog)
        self.save_path_line_edit.setGeometry(QtCore.QRect(190, 270, 81, 20))
        self.save_path_line_edit.setObjectName("save_path_line_edit")
        self.save_label = QtWidgets.QLabel(HTLSAcqSettingsDialog)
        self.save_label.setGeometry(QtCore.QRect(110, 270, 71, 20))
        self.save_label.setObjectName("save_label")
        self.start_acquisition_button = QtWidgets.QPushButton(HTLSAcqSettingsDialog)
        self.start_acquisition_button.setGeometry(QtCore.QRect(140, 330, 111, 23))
        self.start_acquisition_button.setObjectName("start_acquisition_button")
        self.line_2 = QtWidgets.QFrame(HTLSAcqSettingsDialog)
        self.line_2.setGeometry(QtCore.QRect(190, 50, 20, 151))
        self.line_2.setFrameShadow(QtWidgets.QFrame.Plain)
        self.line_2.setLineWidth(4)
        self.line_2.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_2.setObjectName("line_2")
        self.acq_settings_label = QtWidgets.QLabel(HTLSAcqSettingsDialog)
        self.acq_settings_label.setGeometry(QtCore.QRect(80, 10, 241, 31))
        font = QtGui.QFont()
        font.setPointSize(16)
        self.acq_settings_label.setFont(font)
        self.acq_settings_label.setAlignment(QtCore.Qt.AlignCenter)
        self.acq_settings_label.setObjectName("acq_settings_label")
        self.researcher_line_edit = QtWidgets.QLineEdit(HTLSAcqSettingsDialog)
        self.researcher_line_edit.setGeometry(QtCore.QRect(190, 300, 81, 20))
        self.researcher_line_edit.setObjectName("researcher_line_edit")
        self.researcher_label = QtWidgets.QLabel(HTLSAcqSettingsDialog)
        self.researcher_label.setGeometry(QtCore.QRect(120, 300, 61, 20))
        self.researcher_label.setObjectName("researcher_label")
        self.save_acquisition_label = QtWidgets.QLabel(HTLSAcqSettingsDialog)
        self.save_acquisition_label.setGeometry(QtCore.QRect(120, 210, 141, 20))
        self.save_acquisition_label.setAlignment(QtCore.Qt.AlignCenter)
        self.save_acquisition_label.setObjectName("save_acquisition_label")
        self.show_acquisition_dialog_button = QtWidgets.QPushButton(HTLSAcqSettingsDialog)
        self.show_acquisition_dialog_button.setGeometry(QtCore.QRect(130, 360, 131, 23))
        self.show_acquisition_dialog_button.setObjectName("show_acquisition_dialog_button")
        self.line_3 = QtWidgets.QFrame(HTLSAcqSettingsDialog)
        self.line_3.setGeometry(QtCore.QRect(-30, 190, 461, 20))
        font = QtGui.QFont()
        font.setPointSize(8)
        self.line_3.setFont(font)
        self.line_3.setFrameShadow(QtWidgets.QFrame.Plain)
        self.line_3.setLineWidth(4)
        self.line_3.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_3.setObjectName("line_3")
        self.adv_settings_button = QtWidgets.QPushButton(HTLSAcqSettingsDialog)
        self.adv_settings_button.setGeometry(QtCore.QRect(210, 110, 171, 23))
        self.adv_settings_button.setObjectName("adv_settings_button")
        self.adv_settings_label = QtWidgets.QLabel(HTLSAcqSettingsDialog)
        self.adv_settings_label.setGeometry(QtCore.QRect(230, 80, 121, 20))
        self.adv_settings_label.setAlignment(QtCore.Qt.AlignCenter)
        self.adv_settings_label.setObjectName("adv_settings_label")

        self.retranslateUi(HTLSAcqSettingsDialog)
        QtCore.QMetaObject.connectSlotsByName(HTLSAcqSettingsDialog)

    def retranslateUi(self, HTLSAcqSettingsDialog):
        _translate = QtCore.QCoreApplication.translate
        HTLSAcqSettingsDialog.setWindowTitle(_translate("HTLSAcqSettingsDialog", "Acquisition Settings"))
        self.channel_order_move_up_button.setWhatsThis(_translate("HTLSAcqSettingsDialog", "<html><head/><body><p>Moves channel up in channel order list</p></body></html>"))
        self.channel_order_move_up_button.setText(_translate("HTLSAcqSettingsDialog", "Move Up"))
        self.channel_order_move_down_button.setWhatsThis(_translate("HTLSAcqSettingsDialog", "<html><head/><body><p>Moves channel down in channel order list</p></body></html>"))
        self.channel_order_move_down_button.setText(_translate("HTLSAcqSettingsDialog", "Move Down"))
        self.channel_order_list_view.setWhatsThis(_translate("HTLSAcqSettingsDialog", "<html><head/><body><p>Order of channels in Z-stack, Snap, and Video acquisitions from top to bottom</p></body></html>"))
        self.channel_order_label.setText(_translate("HTLSAcqSettingsDialog", "<html><head/><body><p><span style=\" font-weight:600;\">Channel Order</span></p></body></html>"))
        self.browse_button.setWhatsThis(_translate("HTLSAcqSettingsDialog", "<html><head/><body><p>Browse and choose directory for acquisition to be saved</p></body></html>"))
        self.browse_button.setText(_translate("HTLSAcqSettingsDialog", "Browse..."))
        self.save_path_line_edit.setWhatsThis(_translate("HTLSAcqSettingsDialog", "<html><head/><body><p>Save location of acquisition</p></body></html>"))
        self.save_label.setText(_translate("HTLSAcqSettingsDialog", "Save Location:"))
        self.start_acquisition_button.setWhatsThis(_translate("HTLSAcqSettingsDialog", "<html><head/><body><p>Starts acquisition from settings set here and the region setup dialog. Also brings up the Acquisition Dialog which will provide updates during the acquisition and has an option to abort the acquisition.</p></body></html>"))
        self.start_acquisition_button.setText(_translate("HTLSAcqSettingsDialog", "Start Acquisition"))
        self.acq_settings_label.setText(_translate("HTLSAcqSettingsDialog", "Acquisition Settings"))
        self.researcher_line_edit.setWhatsThis(_translate("HTLSAcqSettingsDialog", "<html><head/><body><p>Name of researcher</p></body></html>"))
        self.researcher_label.setText(_translate("HTLSAcqSettingsDialog", "Researcher:"))
        self.save_acquisition_label.setText(_translate("HTLSAcqSettingsDialog", "<html><head/><body><p><span style=\" font-weight:600;\">Save/Acquisition Start</span></p></body></html>"))
        self.show_acquisition_dialog_button.setWhatsThis(_translate("HTLSAcqSettingsDialog", "<html><head/><body><p>show the acquisition dialog, which povides updates of current acquisition.</p></body></html>"))
        self.show_acquisition_dialog_button.setText(_translate("HTLSAcqSettingsDialog", "Show Acquisition Dialog"))
        self.adv_settings_button.setWhatsThis(_translate("HTLSAcqSettingsDialog", "<html><head/><body><p>Moves channel down in channel order list</p></body></html>"))
        self.adv_settings_button.setText(_translate("HTLSAcqSettingsDialog", "Advanced Acquisition Settings"))
        self.adv_settings_label.setText(_translate("HTLSAcqSettingsDialog", "<html><head/><body><p><span style=\" font-weight:600;\">Advanced Settings</span></p></body></html>"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    HTLSAcqSettingsDialog = QtWidgets.QDialog()
    ui = Ui_HTLSAcqSettingsDialog()
    ui.setupUi(HTLSAcqSettingsDialog)
    HTLSAcqSettingsDialog.show()
    sys.exit(app.exec_())
