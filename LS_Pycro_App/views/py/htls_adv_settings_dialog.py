# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\marim\Desktop\LS_Pycro_App\LS_Pycro_App\views\ui\HTLSAdvSettingsDialog.ui'
#
# Created by: PyQt5 UI code generator 5.15.10
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_HTLSAdvSettingsDialog(object):
    def setupUi(self, HTLSAdvSettingsDialog):
        HTLSAdvSettingsDialog.setObjectName("HTLSAdvSettingsDialog")
        HTLSAdvSettingsDialog.resize(437, 381)
        self.z_stack_exp_unit_label = QtWidgets.QLabel(HTLSAdvSettingsDialog)
        self.z_stack_exp_unit_label.setGeometry(QtCore.QRect(190, 120, 21, 16))
        self.z_stack_exp_unit_label.setAlignment(QtCore.Qt.AlignCenter)
        self.z_stack_exp_unit_label.setObjectName("z_stack_exp_unit_label")
        self.z_stack_settings_label = QtWidgets.QLabel(HTLSAdvSettingsDialog)
        self.z_stack_settings_label.setGeometry(QtCore.QRect(60, 10, 101, 20))
        self.z_stack_settings_label.setAlignment(QtCore.Qt.AlignCenter)
        self.z_stack_settings_label.setObjectName("z_stack_settings_label")
        self.z_stack_exposure_line_edit = QtWidgets.QLineEdit(HTLSAdvSettingsDialog)
        self.z_stack_exposure_line_edit.setGeometry(QtCore.QRect(130, 120, 61, 20))
        self.z_stack_exposure_line_edit.setObjectName("z_stack_exposure_line_edit")
        self.z_stack_exposure_label = QtWidgets.QLabel(HTLSAdvSettingsDialog)
        self.z_stack_exposure_label.setGeometry(QtCore.QRect(10, 120, 111, 20))
        self.z_stack_exposure_label.setObjectName("z_stack_exposure_label")
        self.video_spectral_check_box = QtWidgets.QCheckBox(HTLSAdvSettingsDialog)
        self.video_spectral_check_box.setGeometry(QtCore.QRect(50, 200, 121, 20))
        self.video_spectral_check_box.setObjectName("video_spectral_check_box")
        self.video_settings_label = QtWidgets.QLabel(HTLSAdvSettingsDialog)
        self.video_settings_label.setGeometry(QtCore.QRect(40, 170, 101, 20))
        self.video_settings_label.setAlignment(QtCore.Qt.AlignCenter)
        self.video_settings_label.setObjectName("video_settings_label")
        self.stage_speed_label = QtWidgets.QLabel(HTLSAdvSettingsDialog)
        self.stage_speed_label.setGeometry(QtCore.QRect(40, 60, 71, 20))
        self.stage_speed_label.setObjectName("stage_speed_label")
        self.stage_speed_combo_box = QtWidgets.QComboBox(HTLSAdvSettingsDialog)
        self.stage_speed_combo_box.setGeometry(QtCore.QRect(110, 60, 69, 22))
        self.stage_speed_combo_box.setObjectName("stage_speed_combo_box")
        self.line_2 = QtWidgets.QFrame(HTLSAdvSettingsDialog)
        self.line_2.setGeometry(QtCore.QRect(200, -100, 20, 361))
        self.line_2.setFrameShadow(QtWidgets.QFrame.Plain)
        self.line_2.setLineWidth(4)
        self.line_2.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_2.setObjectName("line_2")
        self.save_label = QtWidgets.QLabel(HTLSAdvSettingsDialog)
        self.save_label.setGeometry(QtCore.QRect(220, 220, 91, 20))
        self.save_label.setObjectName("save_label")
        self.backup_directory_browse_button = QtWidgets.QPushButton(HTLSAdvSettingsDialog)
        self.backup_directory_browse_button.setGeometry(QtCore.QRect(280, 190, 75, 23))
        self.backup_directory_browse_button.setObjectName("backup_directory_browse_button")
        self.backup_directory_line_edit = QtWidgets.QLineEdit(HTLSAdvSettingsDialog)
        self.backup_directory_line_edit.setGeometry(QtCore.QRect(310, 220, 111, 20))
        self.backup_directory_line_edit.setObjectName("backup_directory_line_edit")
        self.backup_directory_check_box = QtWidgets.QCheckBox(HTLSAdvSettingsDialog)
        self.backup_directory_check_box.setGeometry(QtCore.QRect(290, 170, 71, 20))
        self.backup_directory_check_box.setObjectName("backup_directory_check_box")
        self.z_stack_spectral_check_box = QtWidgets.QCheckBox(HTLSAdvSettingsDialog)
        self.z_stack_spectral_check_box.setGeometry(QtCore.QRect(60, 30, 121, 20))
        self.z_stack_spectral_check_box.setObjectName("z_stack_spectral_check_box")
        self.lsrm_check_box = QtWidgets.QCheckBox(HTLSAdvSettingsDialog)
        self.lsrm_check_box.setGeometry(QtCore.QRect(300, 70, 51, 20))
        self.lsrm_check_box.setObjectName("lsrm_check_box")
        self.lsrm_label = QtWidgets.QLabel(HTLSAdvSettingsDialog)
        self.lsrm_label.setGeometry(QtCore.QRect(250, 50, 151, 20))
        self.lsrm_label.setAlignment(QtCore.Qt.AlignCenter)
        self.lsrm_label.setObjectName("lsrm_label")
        self.line_7 = QtWidgets.QFrame(HTLSAdvSettingsDialog)
        self.line_7.setGeometry(QtCore.QRect(-30, 140, 491, 20))
        font = QtGui.QFont()
        font.setPointSize(8)
        self.line_7.setFont(font)
        self.line_7.setFrameShadow(QtWidgets.QFrame.Plain)
        self.line_7.setLineWidth(4)
        self.line_7.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_7.setObjectName("line_7")
        self.backup_label = QtWidgets.QLabel(HTLSAdvSettingsDialog)
        self.backup_label.setGeometry(QtCore.QRect(240, 150, 151, 20))
        self.backup_label.setAlignment(QtCore.Qt.AlignCenter)
        self.backup_label.setObjectName("backup_label")
        self.custom_exposure_check_box = QtWidgets.QCheckBox(HTLSAdvSettingsDialog)
        self.custom_exposure_check_box.setGeometry(QtCore.QRect(30, 90, 141, 20))
        self.custom_exposure_check_box.setObjectName("custom_exposure_check_box")
        self.end_videos_check_box = QtWidgets.QCheckBox(HTLSAdvSettingsDialog)
        self.end_videos_check_box.setGeometry(QtCore.QRect(160, 290, 141, 20))
        self.end_videos_check_box.setObjectName("end_videos_check_box")
        self.end_videos_exposure_label = QtWidgets.QLabel(HTLSAdvSettingsDialog)
        self.end_videos_exposure_label.setGeometry(QtCore.QRect(130, 350, 81, 20))
        self.end_videos_exposure_label.setObjectName("end_videos_exposure_label")
        self.end_videos_num_frames_label = QtWidgets.QLabel(HTLSAdvSettingsDialog)
        self.end_videos_num_frames_label.setGeometry(QtCore.QRect(110, 320, 101, 20))
        self.end_videos_num_frames_label.setObjectName("end_videos_num_frames_label")
        self.end_videos_label = QtWidgets.QLabel(HTLSAdvSettingsDialog)
        self.end_videos_label.setGeometry(QtCore.QRect(160, 270, 101, 20))
        self.end_videos_label.setAlignment(QtCore.Qt.AlignCenter)
        self.end_videos_label.setObjectName("end_videos_label")
        self.end_videos_num_frames_line_edit = QtWidgets.QLineEdit(HTLSAdvSettingsDialog)
        self.end_videos_num_frames_line_edit.setGeometry(QtCore.QRect(210, 320, 61, 20))
        self.end_videos_num_frames_line_edit.setObjectName("end_videos_num_frames_line_edit")
        self.end_videos_exposure_line_edit = QtWidgets.QLineEdit(HTLSAdvSettingsDialog)
        self.end_videos_exposure_line_edit.setGeometry(QtCore.QRect(210, 350, 61, 20))
        self.end_videos_exposure_line_edit.setObjectName("end_videos_exposure_line_edit")
        self.line_8 = QtWidgets.QFrame(HTLSAdvSettingsDialog)
        self.line_8.setGeometry(QtCore.QRect(0, 250, 491, 20))
        font = QtGui.QFont()
        font.setPointSize(8)
        self.line_8.setFont(font)
        self.line_8.setFrameShadow(QtWidgets.QFrame.Plain)
        self.line_8.setLineWidth(4)
        self.line_8.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_8.setObjectName("line_8")

        self.retranslateUi(HTLSAdvSettingsDialog)
        QtCore.QMetaObject.connectSlotsByName(HTLSAdvSettingsDialog)

    def retranslateUi(self, HTLSAdvSettingsDialog):
        _translate = QtCore.QCoreApplication.translate
        HTLSAdvSettingsDialog.setWindowTitle(_translate("HTLSAdvSettingsDialog", "Advanced Settings"))
        self.z_stack_exp_unit_label.setText(_translate("HTLSAdvSettingsDialog", "ms"))
        self.z_stack_settings_label.setText(_translate("HTLSAdvSettingsDialog", "<html><head/><body><p><span style=\" font-weight:600;\">Z-Stack Settings</span></p></body></html>"))
        self.z_stack_exposure_line_edit.setWhatsThis(_translate("HTLSAdvSettingsDialog", "<html><head/><body><p>Exposure time for use in Z-stack. </p><p>If spectral Z-stack is enabled, exposure time is only limited by camera\'s min/max exposure time. </p><p>If both spectral Z-stack and custom exposure are disabled, exposure time will be ~ 1/stage_speed</p><p>If spectral Z-stack is disabaled but custom exposure is enabled, allowed exposure time is determined by camera\'s allowed exposure in external trigger mode. See Hamamatsu documentation for more details.</p></body></html>"))
        self.z_stack_exposure_label.setText(_translate("HTLSAdvSettingsDialog", "Z-Stack Exposure Time:"))
        self.video_spectral_check_box.setWhatsThis(_translate("HTLSAdvSettingsDialog", "<html><head/><body><p>If checked, videos will be performed by alternating between channels until the desired number of images are acquired per channel.</p><p>Otherwise, a full video will be taken in each channel one at a time.</p></body></html>"))
        self.video_spectral_check_box.setText(_translate("HTLSAdvSettingsDialog", "Spectral Video"))
        self.video_settings_label.setText(_translate("HTLSAdvSettingsDialog", "<html><head/><body><p><span style=\" font-weight:600;\">Video Settings</span></p></body></html>"))
        self.stage_speed_label.setText(_translate("HTLSAdvSettingsDialog", "Stage Speed:"))
        self.stage_speed_combo_box.setWhatsThis(_translate("HTLSAdvSettingsDialog", "<html><head/><body><p>Sets stage speed to be used during continuous Z-stack. Note that this doesn\'t apply if Spectral Z-stack is enabled.</p><p>Since 30 is the full sensor maximum framerate of the PCO camera, 30 um/s is the current default speed. </p></body></html>"))
        self.save_label.setText(_translate("HTLSAdvSettingsDialog", "Backup Directory:"))
        self.backup_directory_browse_button.setWhatsThis(_translate("HTLSAdvSettingsDialog", "<html><head/><body><p>Browse and choose backup directory.</p></body></html>"))
        self.backup_directory_browse_button.setText(_translate("HTLSAdvSettingsDialog", "Browse..."))
        self.backup_directory_line_edit.setWhatsThis(_translate("HTLSAdvSettingsDialog", "<html><head/><body><p>Backup directory.</p></body></html>"))
        self.backup_directory_check_box.setWhatsThis(_translate("HTLSAdvSettingsDialog", "<html><head/><body><p>Let\'s you choose a backup directory in case the primary directory runs out of space.</p></body></html>"))
        self.backup_directory_check_box.setText(_translate("HTLSAdvSettingsDialog", "Enable"))
        self.z_stack_spectral_check_box.setWhatsThis(_translate("HTLSAdvSettingsDialog", "<html><head/><body><p>If checked, Z-stack will be performed in the following way:</p><p>1. stage will move to first position.</p><p>2. Images will be taken with each channel selected.</p><p>3. stage will move by the set step size.</p><p>4. repeat 2 and 3 until end position is reached.</p><p>Otherwise, Z-stack will be performed with continuous stage motion, acquiring one channel at a time.</p></body></html>"))
        self.z_stack_spectral_check_box.setText(_translate("HTLSAdvSettingsDialog", "Spectral Z-stack"))
        self.lsrm_check_box.setWhatsThis(_translate("HTLSAdvSettingsDialog", "<html><head/><body><p>If checked, will enable Lightsheet Readout Mode (rolling shutter). Note that this should be configured in the Galvo Setup part of the application.</p><p><br/></p></body></html>"))
        self.lsrm_check_box.setText(_translate("HTLSAdvSettingsDialog", "Enable"))
        self.lsrm_label.setText(_translate("HTLSAdvSettingsDialog", "<html><head/><body><p><span style=\" font-weight:600;\">Lightsheet Readout Mode</span></p></body></html>"))
        self.backup_label.setText(_translate("HTLSAdvSettingsDialog", "<html><head/><body><p><span style=\" font-weight:600;\">Backup Directory</span></p></body></html>"))
        self.custom_exposure_check_box.setWhatsThis(_translate("HTLSAdvSettingsDialog", "<html><head/><body><p>If checked, allows user to set custom exposure time for z-stack.</p><p>Due to how the camera triggering system works, when this option is enabled, only certain exposure time ranges are allowed.</p><p>For example, if stage speed is 30 um/s, the maximum exposure time is ~23 ms. See Hamamtsu edge trigger mode for more information.</p><p><br/></p></body></html>"))
        self.custom_exposure_check_box.setText(_translate("HTLSAdvSettingsDialog", "Enable Custom Exposure"))
        self.end_videos_check_box.setWhatsThis(_translate("HTLSAdvSettingsDialog", "<html><head/><body><p>If enabled, will take a video with the settings given at the end of an acquisition (after all time points have been acquired) at position 1 of each sample with imaging enabled.</p><p> End videos are intended to be taken at the end of a time series to ensure fish are still alive at the end. Will be saved in the Acquisition folder under the name &quot;end videos.&quot;</p><p><br/></p></body></html>"))
        self.end_videos_check_box.setText(_translate("HTLSAdvSettingsDialog", "Enable End Videos"))
        self.end_videos_exposure_label.setText(_translate("HTLSAdvSettingsDialog", "Exposure Time:"))
        self.end_videos_num_frames_label.setText(_translate("HTLSAdvSettingsDialog", "Number of Frames:"))
        self.end_videos_label.setText(_translate("HTLSAdvSettingsDialog", "<html><head/><body><p><span style=\" font-weight:600;\">End Videos</span></p></body></html>"))
        self.end_videos_num_frames_line_edit.setWhatsThis(_translate("HTLSAdvSettingsDialog", "<html><head/><body><p>Exposure time for use in Z-stack. </p><p>If spectral Z-stack is enabled, exposure time is only limited by camera\'s min/max exposure time. </p><p>If both spectral Z-stack and custom exposure are disabled, exposure time will be ~ 1/stage_speed</p><p>If spectral Z-stack is disabaled but custom exposure is enabled, allowed exposure time is determined by camera\'s allowed exposure in external trigger mode. See Hamamatsu documentation for more details.</p></body></html>"))
        self.end_videos_exposure_line_edit.setWhatsThis(_translate("HTLSAdvSettingsDialog", "<html><head/><body><p>Exposure time for use in Z-stack. </p><p>If spectral Z-stack is enabled, exposure time is only limited by camera\'s min/max exposure time. </p><p>If both spectral Z-stack and custom exposure are disabled, exposure time will be ~ 1/stage_speed</p><p>If spectral Z-stack is disabaled but custom exposure is enabled, allowed exposure time is determined by camera\'s allowed exposure in external trigger mode. See Hamamatsu documentation for more details.</p></body></html>"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    HTLSAdvSettingsDialog = QtWidgets.QDialog()
    ui = Ui_HTLSAdvSettingsDialog()
    ui.setupUi(HTLSAdvSettingsDialog)
    HTLSAdvSettingsDialog.show()
    sys.exit(app.exec_())
