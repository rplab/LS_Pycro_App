# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\Raghu\Desktop\Microscope Software\LS_Pycro_App\LS_Pycro_App\views\ui_files\AcqSettingsDialog.ui'
#
# Created by: PyQt5 UI code generator 5.15.4
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_AcqSettingsDialog(object):
    def setupUi(self, AcqSettingsDialog):
        AcqSettingsDialog.setObjectName("AcqSettingsDialog")
        AcqSettingsDialog.resize(398, 457)
        self.time_points_check_box = QtWidgets.QCheckBox(AcqSettingsDialog)
        self.time_points_check_box.setGeometry(QtCore.QRect(60, 90, 81, 17))
        self.time_points_check_box.setObjectName("time_points_check_box")
        self.num_time_points_line_edit = QtWidgets.QLineEdit(AcqSettingsDialog)
        self.num_time_points_line_edit.setGeometry(QtCore.QRect(80, 120, 61, 20))
        self.num_time_points_line_edit.setObjectName("num_time_points_line_edit")
        self.time_points_interval_line_edit = QtWidgets.QLineEdit(AcqSettingsDialog)
        self.time_points_interval_line_edit.setGeometry(QtCore.QRect(80, 150, 61, 20))
        self.time_points_interval_line_edit.setObjectName("time_points_interval_line_edit")
        self.channel_order_move_up_button = QtWidgets.QPushButton(AcqSettingsDialog)
        self.channel_order_move_up_button.setGeometry(QtCore.QRect(210, 110, 75, 23))
        self.channel_order_move_up_button.setObjectName("channel_order_move_up_button")
        self.channel_order_move_down_button = QtWidgets.QPushButton(AcqSettingsDialog)
        self.channel_order_move_down_button.setGeometry(QtCore.QRect(210, 150, 75, 23))
        self.channel_order_move_down_button.setObjectName("channel_order_move_down_button")
        self.channel_order_list_view = QtWidgets.QListView(AcqSettingsDialog)
        self.channel_order_list_view.setGeometry(QtCore.QRect(290, 90, 101, 101))
        self.channel_order_list_view.setObjectName("channel_order_list_view")
        self.channel_order_label = QtWidgets.QLabel(AcqSettingsDialog)
        self.channel_order_label.setGeometry(QtCore.QRect(250, 60, 101, 20))
        self.channel_order_label.setAlignment(QtCore.Qt.AlignCenter)
        self.channel_order_label.setObjectName("channel_order_label")
        self.count_label = QtWidgets.QLabel(AcqSettingsDialog)
        self.count_label.setGeometry(QtCore.QRect(40, 120, 31, 16))
        self.count_label.setObjectName("count_label")
        self.interval_label = QtWidgets.QLabel(AcqSettingsDialog)
        self.interval_label.setGeometry(QtCore.QRect(30, 150, 51, 16))
        self.interval_label.setObjectName("interval_label")
        self.browse_button = QtWidgets.QPushButton(AcqSettingsDialog)
        self.browse_button.setGeometry(QtCore.QRect(160, 310, 75, 23))
        self.browse_button.setObjectName("browse_button")
        self.save_path_line_edit = QtWidgets.QLineEdit(AcqSettingsDialog)
        self.save_path_line_edit.setGeometry(QtCore.QRect(190, 340, 81, 20))
        self.save_path_line_edit.setObjectName("save_path_line_edit")
        self.save_label = QtWidgets.QLabel(AcqSettingsDialog)
        self.save_label.setGeometry(QtCore.QRect(110, 340, 71, 20))
        self.save_label.setObjectName("save_label")
        self.start_acquisition_button = QtWidgets.QPushButton(AcqSettingsDialog)
        self.start_acquisition_button.setGeometry(QtCore.QRect(140, 400, 111, 23))
        self.start_acquisition_button.setObjectName("start_acquisition_button")
        self.total_images_label = QtWidgets.QLabel(AcqSettingsDialog)
        self.total_images_label.setGeometry(QtCore.QRect(30, 210, 71, 16))
        self.total_images_label.setObjectName("total_images_label")
        self.total_images_line_edit = QtWidgets.QLineEdit(AcqSettingsDialog)
        self.total_images_line_edit.setGeometry(QtCore.QRect(110, 210, 61, 20))
        self.total_images_line_edit.setObjectName("total_images_line_edit")
        self.memory_label = QtWidgets.QLabel(AcqSettingsDialog)
        self.memory_label.setGeometry(QtCore.QRect(30, 240, 71, 16))
        self.memory_label.setObjectName("memory_label")
        self.memory_line_edit = QtWidgets.QLineEdit(AcqSettingsDialog)
        self.memory_line_edit.setGeometry(QtCore.QRect(110, 240, 61, 20))
        self.memory_line_edit.setObjectName("memory_line_edit")
        self.num_images_per_label = QtWidgets.QLabel(AcqSettingsDialog)
        self.num_images_per_label.setGeometry(QtCore.QRect(10, 180, 91, 20))
        self.num_images_per_label.setObjectName("num_images_per_label")
        self.num_images_per_line_edit = QtWidgets.QLineEdit(AcqSettingsDialog)
        self.num_images_per_line_edit.setGeometry(QtCore.QRect(110, 180, 61, 20))
        self.num_images_per_line_edit.setObjectName("num_images_per_line_edit")
        self.line_2 = QtWidgets.QFrame(AcqSettingsDialog)
        self.line_2.setGeometry(QtCore.QRect(190, 50, 20, 221))
        self.line_2.setFrameShadow(QtWidgets.QFrame.Plain)
        self.line_2.setLineWidth(4)
        self.line_2.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_2.setObjectName("line_2")
        self.acq_settings_label = QtWidgets.QLabel(AcqSettingsDialog)
        self.acq_settings_label.setGeometry(QtCore.QRect(80, 10, 241, 31))
        font = QtGui.QFont()
        font.setPointSize(16)
        self.acq_settings_label.setFont(font)
        self.acq_settings_label.setAlignment(QtCore.Qt.AlignCenter)
        self.acq_settings_label.setObjectName("acq_settings_label")
        self.line_4 = QtWidgets.QFrame(AcqSettingsDialog)
        self.line_4.setGeometry(QtCore.QRect(-60, 40, 531, 20))
        font = QtGui.QFont()
        font.setPointSize(8)
        self.line_4.setFont(font)
        self.line_4.setFrameShadow(QtWidgets.QFrame.Plain)
        self.line_4.setLineWidth(4)
        self.line_4.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_4.setObjectName("line_4")
        self.memory_unit_label = QtWidgets.QLabel(AcqSettingsDialog)
        self.memory_unit_label.setGeometry(QtCore.QRect(170, 240, 21, 16))
        self.memory_unit_label.setAlignment(QtCore.Qt.AlignCenter)
        self.memory_unit_label.setObjectName("memory_unit_label")
        self.researcher_line_edit = QtWidgets.QLineEdit(AcqSettingsDialog)
        self.researcher_line_edit.setGeometry(QtCore.QRect(190, 370, 81, 20))
        self.researcher_line_edit.setObjectName("researcher_line_edit")
        self.researcher_label = QtWidgets.QLabel(AcqSettingsDialog)
        self.researcher_label.setGeometry(QtCore.QRect(120, 370, 61, 20))
        self.researcher_label.setObjectName("researcher_label")
        self.save_acquisition_label = QtWidgets.QLabel(AcqSettingsDialog)
        self.save_acquisition_label.setGeometry(QtCore.QRect(120, 280, 141, 20))
        self.save_acquisition_label.setAlignment(QtCore.Qt.AlignCenter)
        self.save_acquisition_label.setObjectName("save_acquisition_label")
        self.interval_label_2 = QtWidgets.QLabel(AcqSettingsDialog)
        self.interval_label_2.setGeometry(QtCore.QRect(150, 150, 31, 16))
        self.interval_label_2.setObjectName("interval_label_2")
        self.show_acquisition_dialog_button = QtWidgets.QPushButton(AcqSettingsDialog)
        self.show_acquisition_dialog_button.setGeometry(QtCore.QRect(130, 430, 131, 23))
        self.show_acquisition_dialog_button.setObjectName("show_acquisition_dialog_button")
        self.line_3 = QtWidgets.QFrame(AcqSettingsDialog)
        self.line_3.setGeometry(QtCore.QRect(-40, 260, 461, 20))
        font = QtGui.QFont()
        font.setPointSize(8)
        self.line_3.setFont(font)
        self.line_3.setFrameShadow(QtWidgets.QFrame.Plain)
        self.line_3.setLineWidth(4)
        self.line_3.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_3.setObjectName("line_3")
        self.adv_settings_button = QtWidgets.QPushButton(AcqSettingsDialog)
        self.adv_settings_button.setGeometry(QtCore.QRect(220, 240, 171, 23))
        self.adv_settings_button.setObjectName("adv_settings_button")
        self.adv_settings_label = QtWidgets.QLabel(AcqSettingsDialog)
        self.adv_settings_label.setGeometry(QtCore.QRect(240, 210, 121, 20))
        self.adv_settings_label.setAlignment(QtCore.Qt.AlignCenter)
        self.adv_settings_label.setObjectName("adv_settings_label")
        self.line_5 = QtWidgets.QFrame(AcqSettingsDialog)
        self.line_5.setGeometry(QtCore.QRect(200, 190, 461, 20))
        font = QtGui.QFont()
        font.setPointSize(8)
        self.line_5.setFont(font)
        self.line_5.setFrameShadow(QtWidgets.QFrame.Plain)
        self.line_5.setLineWidth(4)
        self.line_5.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_5.setObjectName("line_5")
        self.time_points_label = QtWidgets.QLabel(AcqSettingsDialog)
        self.time_points_label.setGeometry(QtCore.QRect(40, 60, 101, 20))
        self.time_points_label.setAlignment(QtCore.Qt.AlignCenter)
        self.time_points_label.setObjectName("time_points_label")

        self.retranslateUi(AcqSettingsDialog)
        QtCore.QMetaObject.connectSlotsByName(AcqSettingsDialog)

    def retranslateUi(self, AcqSettingsDialog):
        _translate = QtCore.QCoreApplication.translate
        AcqSettingsDialog.setWindowTitle(_translate("AcqSettingsDialog", "Acquisition Settings"))
        self.time_points_check_box.setWhatsThis(_translate("AcqSettingsDialog", "<html><head/><body><p>Enables time series.</p></body></html>"))
        self.time_points_check_box.setText(_translate("AcqSettingsDialog", "Time points"))
        self.num_time_points_line_edit.setWhatsThis(_translate("AcqSettingsDialog", "<html><head/><body><p>Number of time points in time series</p></body></html>"))
        self.time_points_interval_line_edit.setWhatsThis(_translate("AcqSettingsDialog", "<html><head/><body><p>Interval between time points in seconds</p></body></html>"))
        self.channel_order_move_up_button.setWhatsThis(_translate("AcqSettingsDialog", "<html><head/><body><p>Moves channel up in channel order list</p></body></html>"))
        self.channel_order_move_up_button.setText(_translate("AcqSettingsDialog", "Move Up"))
        self.channel_order_move_down_button.setWhatsThis(_translate("AcqSettingsDialog", "<html><head/><body><p>Moves channel down in channel order list</p></body></html>"))
        self.channel_order_move_down_button.setText(_translate("AcqSettingsDialog", "Move Down"))
        self.channel_order_list_view.setWhatsThis(_translate("AcqSettingsDialog", "<html><head/><body><p>Order of channels in Z-stack, Snap, and Video acquisitions from top to bottom</p></body></html>"))
        self.channel_order_label.setText(_translate("AcqSettingsDialog", "<html><head/><body><p><span style=\" font-weight:600;\">Channel Order</span></p></body></html>"))
        self.count_label.setText(_translate("AcqSettingsDialog", "Count:"))
        self.interval_label.setText(_translate("AcqSettingsDialog", "Interval:"))
        self.browse_button.setWhatsThis(_translate("AcqSettingsDialog", "<html><head/><body><p>Browse and choose directory for acquisition to be saved</p></body></html>"))
        self.browse_button.setText(_translate("AcqSettingsDialog", "Browse..."))
        self.save_path_line_edit.setWhatsThis(_translate("AcqSettingsDialog", "<html><head/><body><p>Save location of acquisition</p></body></html>"))
        self.save_label.setText(_translate("AcqSettingsDialog", "Save Location:"))
        self.start_acquisition_button.setWhatsThis(_translate("AcqSettingsDialog", "<html><head/><body><p>Starts acquisition from settings set here and the region setup dialog. Also brings up the Acquisition Dialog which will provide updates during the acquisition and has an option to abort the acquisition.</p></body></html>"))
        self.start_acquisition_button.setText(_translate("AcqSettingsDialog", "Start Acquisition"))
        self.total_images_label.setText(_translate("AcqSettingsDialog", "Total Images:"))
        self.total_images_line_edit.setWhatsThis(_translate("AcqSettingsDialog", "<html><head/><body><p>Total number of images taken during the entire acquisition</p></body></html>"))
        self.memory_label.setText(_translate("AcqSettingsDialog", "Total Memory:"))
        self.memory_line_edit.setWhatsThis(_translate("AcqSettingsDialog", "<html><head/><body><p>Total amount of data taken during the entire acquisition</p></body></html>"))
        self.num_images_per_label.setText(_translate("AcqSettingsDialog", "Images per point:"))
        self.num_images_per_line_edit.setWhatsThis(_translate("AcqSettingsDialog", "<html><head/><body><p>Number of images  per time point</p></body></html>"))
        self.acq_settings_label.setText(_translate("AcqSettingsDialog", "Acquisition Settings"))
        self.memory_unit_label.setText(_translate("AcqSettingsDialog", "Gb"))
        self.researcher_line_edit.setWhatsThis(_translate("AcqSettingsDialog", "<html><head/><body><p>Name of researcher</p></body></html>"))
        self.researcher_label.setText(_translate("AcqSettingsDialog", "Researcher:"))
        self.save_acquisition_label.setText(_translate("AcqSettingsDialog", "<html><head/><body><p><span style=\" font-weight:600;\">Save/Acquisition Start</span></p></body></html>"))
        self.interval_label_2.setText(_translate("AcqSettingsDialog", "sec"))
        self.show_acquisition_dialog_button.setWhatsThis(_translate("AcqSettingsDialog", "<html><head/><body><p>show the acquisition dialog, which povides updates of current acquisition.</p></body></html>"))
        self.show_acquisition_dialog_button.setText(_translate("AcqSettingsDialog", "Show Acquisition Dialog"))
        self.adv_settings_button.setWhatsThis(_translate("AcqSettingsDialog", "<html><head/><body><p>Moves channel down in channel order list</p></body></html>"))
        self.adv_settings_button.setText(_translate("AcqSettingsDialog", "Advanced Acquisition Settings"))
        self.adv_settings_label.setText(_translate("AcqSettingsDialog", "<html><head/><body><p><span style=\" font-weight:600;\">Advanced Settings</span></p></body></html>"))
        self.time_points_label.setText(_translate("AcqSettingsDialog", "<html><head/><body><p><span style=\" font-weight:600;\">Time Points</span></p></body></html>"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    AcqSettingsDialog = QtWidgets.QDialog()
    ui = Ui_AcqSettingsDialog()
    ui.setupUi(AcqSettingsDialog)
    AcqSettingsDialog.show()
    sys.exit(app.exec_())
