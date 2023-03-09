import sys
import logging
import contextlib
from PyQt5 import QtGui
from hardware import galvo, galvo_settings, camera, plc, exceptions
from views.shared import GalvoDialog
from utils import globals
from utils.pycro import studio


class GalvoController(object):
    """
    As stated above, this class interacts with the GalvoDialog GUI and the
    GalvoCommands class. The GalvoCommands class sets up the DAQ controlled galvo
    mirrors both for general use in Micro-Manager and for image acquisitions.

    Notes:
    - When setting an lsrm-value, you'll notice if self.galvo_dialog.scanning_check_box.isChecked() is called.
    Since changing values requires the lsrm() scanning method to be called AND the camera lsrm properties to be 
    updated, checking if it's scanning means that we can change the values without setting the hardware.

    Future Changes:
    - Changes in combo box/check box could use switch statements instead of if statements. Might be
      useful if more modes are added. Could even use enum.

    - Combine laser delay and cam delay into one single delay value where positive is cam delay and negative is laser
      delay.
    """

    _DSLM_NAME = "Normal DSLM"
    _LSRM_NAME = "Lightsheet Readout Mode"
    # step sizes for galvoGalvo buttons
    OFFSET_SMALL_STEP = 0.01
    OFFSET_BIG_STEP = 0.1
    FOCUS_SMALL_STEP = 0.001
    FOCUS_BIG_STEP = 0.01
    DELAY_STEP = .01
    NUM_DECIMAL_PLACES = 3

    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)
        self.galvo_dialog = GalvoDialog()
        # If more scanning modes are made in the future, use enum instead of bool and strings
        self._lsrm_bool = False
        # Set scanning combo box model
        self._scan_mode_model = QtGui.QStandardItemModel()
        self.galvo_dialog.scan_mode_combo_box.setModel(self._scan_mode_model)

        self._scan_mode_model.appendRow(QtGui.QStandardItem(GalvoController._DSLM_NAME))
        self._scan_mode_model.appendRow(QtGui.QStandardItem(GalvoController._LSRM_NAME))

        # Initialize event handlers and validators
        self.galvo_dialog.offset_big_neg_button.clicked.connect(self._offset_big_neg_button_clicked)
        self.galvo_dialog.offset_small_neg_button.clicked.connect(self._offset_small_neg_button_clicked)
        self.galvo_dialog.offset_small_pos_button.clicked.connect(self._offset_small_pos_button_clicked)
        self.galvo_dialog.offset_big_pos_button.clicked.connect(self._offset_big_pos_button_clicked)
        self.galvo_dialog.focus_big_neg_button.clicked.connect(self._focus_big_neg_button_clicked)
        self.galvo_dialog.focus_small_neg_button.clicked.connect(self._focus_small_neg_button_clicked)
        self.galvo_dialog.focus_small_pos_button.clicked.connect(self._focus_small_pos_button_clicked)
        self.galvo_dialog.focus_big_pos_button.clicked.connect(self._focus_big_pos_button_clicked)
        self.galvo_dialog.width_big_neg_button.clicked.connect(self._width_big_neg_button_clicked)
        self.galvo_dialog.width_small_neg_button.clicked.connect(self._width_small_neg_button_clicked)
        self.galvo_dialog.width_small_pos_button.clicked.connect(self._width_small_pos_button_clicked)
        self.galvo_dialog.width_big_pos_button.clicked.connect(self._width_big_pos_button_clicked)
        self.galvo_dialog.lsrm_set_lower_button.clicked.connect(self._set_lower_limit_button_clicked)
        self.galvo_dialog.lsrm_set_upper_button.clicked.connect(self._set_upper_limit_button_clicked)
        self.galvo_dialog.framerate_neg_button.clicked.connect(self._framerate_neg_button_clicked)
        self.galvo_dialog.framerate_pos_button.clicked.connect(self._framerate_pos_button_clicked)
        self.galvo_dialog.cam_delay_neg_button.clicked.connect(self._cam_delay_neg_button_clicked)
        self.galvo_dialog.cam_delay_pos_button.clicked.connect(self._cam_delay_pos_button_clicked)
        self.galvo_dialog.laser_delay_neg_button.clicked.connect(self._laser_delay_neg_button_clicked)
        self.galvo_dialog.laser_delay_pos_button.clicked.connect(self._laser_delay_pos_button_clicked)
        self.galvo_dialog.scanning_check_box.clicked.connect(self._scanning_check_box_stage_changed)
        self.galvo_dialog.scan_mode_combo_box.activated.connect(self._scan_mode_combo_box_clicked)
        self.galvo_dialog.offset_line_edit.textEdited.connect(self._offset_line_edit_event)
        self.galvo_dialog.width_line_edit.textEdited.connect(self._width_line_edit_event)
        self.galvo_dialog.focus_line_edit.textEdited.connect(self._focus_line_edit_event)
        self.galvo_dialog.lsrm_lower_line_edit.textEdited.connect(self._lsrm_lower_line_edit_event)
        self.galvo_dialog.lsrm_upper_line_edit.textEdited.connect(self._lsrm_upper_line_edit_event)
        self.galvo_dialog.laser_delay_line_edit.textEdited.connect(self._laser_delay_line_edit_event)
        self.galvo_dialog.cam_delay_line_edit.textEdited.connect(self._cam_delay_line_edit_event)
        self.galvo_dialog.num_lines_line_edit.textEdited.connect(self._num_lines_line_edit_event)

        # Set validators and extra settings
        validator = QtGui.QDoubleValidator()
        validator.setBottom(galvo_settings.WIDTH_BOT_LIMIT)
        validator.setTop(galvo_settings.WIDTH_TOP_LIMIT)
        validator.setDecimals(GalvoController.NUM_DECIMAL_PLACES)
        self.galvo_dialog.width_line_edit.setValidator(validator)

        validator = QtGui.QDoubleValidator()
        validator.setBottom(galvo_settings.OFFSET_BOT_LIMIT)
        validator.setTop(galvo_settings.OFFSET_TOP_LIMIT)
        validator.setDecimals(GalvoController.NUM_DECIMAL_PLACES)
        self.galvo_dialog.offset_line_edit.setValidator(validator)
        self.galvo_dialog.focus_line_edit.setValidator(validator)
        self.galvo_dialog.lsrm_lower_line_edit.setValidator(validator)
        self.galvo_dialog.lsrm_upper_line_edit.setValidator(validator)

        validator = QtGui.QDoubleValidator()
        validator.setBottom(galvo_settings.DELAY_BOT_LIMIT)
        validator.setTop(galvo_settings.DELAY_TOP_LIMIT)
        validator.setDecimals(GalvoController.NUM_DECIMAL_PLACES)
        self.galvo_dialog.cam_delay_line_edit.setValidator(validator)
        self.galvo_dialog.laser_delay_line_edit.setValidator(validator)

        validator = QtGui.QIntValidator()
        validator.setBottom(galvo_settings.NUM_LINES_BOT_LIMIT)
        validator.setTop(galvo_settings.NUM_LINES_TOP_LIMIT)
        self.galvo_dialog.num_lines_line_edit.setValidator(validator)

        self.galvo_dialog.framerate_line_edit.setReadOnly(True)

        # Initialize galvo_settings and dialog values
        self._update_dialog()
        self._set_scanning_mode()

    def _update_dialog(self):
        self._update_dialog_values()
        self._set_dialog_mode()

    # _update_dialog helpers
    def _update_dialog_values(self):
        """
        Updates all values in dialog to match current state of galvo_settings.
        """
        self.galvo_dialog.width_line_edit.setText(globals.get_str_from_float(
            galvo_settings.dslm_scan_width, self.NUM_DECIMAL_PLACES))
        self.galvo_dialog.focus_line_edit.setText(globals.get_str_from_float(
            galvo_settings.focus, self.NUM_DECIMAL_PLACES))
        self.galvo_dialog.lsrm_lower_line_edit.setText(globals.get_str_from_float(
            galvo_settings.lsrm_lower, self.NUM_DECIMAL_PLACES))
        self.galvo_dialog.lsrm_upper_line_edit.setText(globals.get_str_from_float(
            galvo_settings.lsrm_upper, self.NUM_DECIMAL_PLACES))
        self.galvo_dialog.framerate_line_edit.setText(str(galvo_settings.lsrm_framerate))
        self.galvo_dialog.cam_delay_line_edit.setText(globals.get_str_from_float(
            galvo_settings.lsrm_cam_delay, self.NUM_DECIMAL_PLACES))
        self.galvo_dialog.laser_delay_line_edit.setText(globals.get_str_from_float(
            galvo_settings.lsrm_laser_delay, self.NUM_DECIMAL_PLACES))
        self.galvo_dialog.num_lines_line_edit.setText(str(galvo_settings.lsrm_num_lines))

        if self._lsrm_bool:
            self.galvo_dialog.offset_line_edit.setText(globals.get_str_from_float(
                galvo_settings.lsrm_cur_pos, self.NUM_DECIMAL_PLACES))
        else:
            self.galvo_dialog.offset_line_edit.setText(globals.get_str_from_float(
                galvo_settings.dslm_offset, self.NUM_DECIMAL_PLACES))

    def _set_dialog_mode(self):
        """
        Switches between lsrm dialog mode and dslm dialog based on state of lsrm_bool. 
        """
        if self._lsrm_bool:
            self.galvo_dialog.offset_label.setText("Position")
            self.galvo_dialog.resize(438, 350)
        else:
            self.galvo_dialog.offset_label.setText("Offset")
            self.galvo_dialog.resize(438, 140)

        self.galvo_dialog.width_label.setVisible(not self._lsrm_bool)
        self.galvo_dialog.width_line_edit.setVisible(not self._lsrm_bool)
        self.galvo_dialog.width_unit_label.setVisible(not self._lsrm_bool)
        self.galvo_dialog.width_big_neg_button.setVisible(not self._lsrm_bool)
        self.galvo_dialog.width_small_neg_button.setVisible(not self._lsrm_bool)
        self.galvo_dialog.width_small_pos_button.setVisible(not self._lsrm_bool)
        self.galvo_dialog.width_big_pos_button.setVisible(not self._lsrm_bool)

        self.galvo_dialog.lsrm_lower_label.setVisible(self._lsrm_bool)
        self.galvo_dialog.lsrm_lower_line_edit.setVisible(self._lsrm_bool)
        self.galvo_dialog.lsrm_lower_unit_label.setVisible(self._lsrm_bool)
        self.galvo_dialog.lsrm_set_lower_button.setVisible(self._lsrm_bool)

        self.galvo_dialog.lsrm_upper_label.setVisible(self._lsrm_bool)
        self.galvo_dialog.lsrm_upper_line_edit.setVisible(self._lsrm_bool)
        self.galvo_dialog.lsrm_upper_unit_label.setVisible(self._lsrm_bool)
        self.galvo_dialog.lsrm_set_upper_button.setVisible(self._lsrm_bool)

        self.galvo_dialog.framerate_label.setVisible(self._lsrm_bool)
        self.galvo_dialog.framerate_line_edit.setVisible(self._lsrm_bool)
        self.galvo_dialog.framerate_unit_label.setVisible(self._lsrm_bool)
        self.galvo_dialog.framerate_neg_button.setVisible(self._lsrm_bool)
        self.galvo_dialog.framerate_pos_button.setVisible(self._lsrm_bool)

        self.galvo_dialog.cam_delay_label.setVisible(self._lsrm_bool)
        self.galvo_dialog.cam_delay_line_edit.setVisible(self._lsrm_bool)
        self.galvo_dialog.cam_delay_unit_label.setVisible(self._lsrm_bool)
        self.galvo_dialog.cam_delay_neg_button.setVisible(self._lsrm_bool)
        self.galvo_dialog.cam_delay_pos_button.setVisible(self._lsrm_bool)

        self.galvo_dialog.laser_delay_label.setVisible(self._lsrm_bool)
        self.galvo_dialog.laser_delay_line_edit.setVisible(self._lsrm_bool)
        self.galvo_dialog.laser_delay_unit_label.setVisible(self._lsrm_bool)
        self.galvo_dialog.laser_delay_neg_button.setVisible(self._lsrm_bool)
        self.galvo_dialog.laser_delay_pos_button.setVisible(self._lsrm_bool)

        self.galvo_dialog.num_lines_label.setVisible(self._lsrm_bool)
        self.galvo_dialog.num_lines_line_edit.setVisible(self._lsrm_bool)

    def _set_scanning_mode(self):
        with contextlib.suppress(exceptions.GeneralHardwareException):
            if self.galvo_dialog.scanning_check_box.isChecked():
                if self._lsrm_bool:
                    galvo.lsrm()
                else:
                    galvo.dslm()
            else:
                if self._lsrm_bool:
                    galvo.lsrm_not_scanning()
                else:
                    galvo.dslm_not_scanning()

    def _set_camera_properties(self):
        with contextlib.suppress(exceptions.GeneralHardwareException):
            if self._lsrm_bool:
                if self.galvo_dialog.scanning_check_box.isChecked():
                    plc.set_for_continuous_lsrm(galvo_settings.lsrm_framerate)
                    camera.lsrm_mode(galvo_settings.lsrm_ili, galvo_settings.lsrm_num_lines)
                else:
                    camera.default_mode(camera.DEFAULT_EXPOSURE)
            else:
                camera.default_mode(camera.DEFAULT_EXPOSURE)
            # camera setting methods turn live mode off, so this turns it back on!
            studio.live().set_live_mode_on(True)

    def _scan_mode_combo_box_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))

        if self.galvo_dialog.scan_mode_combo_box.currentText() == GalvoController._LSRM_NAME:
            self._lsrm_bool = True
        else:
            self._lsrm_bool = False

        self._set_scanning_mode()
        self._set_camera_properties()

        print(self._lsrm_bool)

        self._update_dialog()

    def _scanning_check_box_stage_changed(self):
        # If checked, starts laser scanning
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._set_scanning_mode()
        self._set_camera_properties()

    def _offset_big_neg_button_clicked(self):
        # Since offset line edit acts as both offset for continuous_scan and
        # current position for lsrm, some extra logic is needed to ensure it's
        # changing the correct attributes.
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        if self._lsrm_bool:
            galvo_settings.lsrm_cur_pos -= GalvoController.OFFSET_BIG_STEP
        else:
            galvo_settings.dslm_offset -= GalvoController.OFFSET_BIG_STEP

        self._set_scanning_mode()
        self._update_dialog()
        galvo_settings.write_to_config()

    def _offset_small_neg_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        if self._lsrm_bool:
            galvo_settings.lsrm_cur_pos -= GalvoController.OFFSET_SMALL_STEP
        else:
            galvo_settings.dslm_offset -= GalvoController.OFFSET_SMALL_STEP

        self._set_scanning_mode()
        self._update_dialog()
        galvo_settings.write_to_config()

    def _offset_small_pos_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        if self._lsrm_bool:
            galvo_settings.lsrm_cur_pos += GalvoController.OFFSET_SMALL_STEP
        else:
            galvo_settings.dslm_offset += GalvoController.OFFSET_SMALL_STEP

        self._set_scanning_mode()
        self._update_dialog()
        galvo_settings.write_to_config()

    def _offset_big_pos_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        if self._lsrm_bool:
            galvo_settings.lsrm_cur_pos += GalvoController.OFFSET_BIG_STEP
        else:
            galvo_settings.dslm_offset += GalvoController.OFFSET_BIG_STEP

        self._set_scanning_mode()
        self._update_dialog()
        galvo_settings.write_to_config()

    def _focus_big_neg_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        galvo_settings.focus -= GalvoController.FOCUS_BIG_STEP

        self._set_scanning_mode()
        self._update_dialog()
        galvo_settings.write_to_config()

    def _focus_small_neg_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        galvo_settings.focus -= GalvoController.FOCUS_SMALL_STEP

        self._set_scanning_mode()
        self._update_dialog()
        galvo_settings.write_to_config()

    def _focus_small_pos_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        galvo_settings.focus += GalvoController.FOCUS_SMALL_STEP

        self._set_scanning_mode()
        self._update_dialog()
        galvo_settings.write_to_config()

    def _focus_big_pos_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        galvo_settings.focus += GalvoController.FOCUS_BIG_STEP

        self._set_scanning_mode()
        self._update_dialog()
        galvo_settings.write_to_config()

    def _width_big_neg_button_clicked(self):
        # Changes scanning range of galvo. Currently, 1.100mV scans
        # the entire camera field.
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        galvo_settings.dslm_scan_width -= GalvoController.OFFSET_BIG_STEP

        self._set_scanning_mode()
        self._update_dialog()
        galvo_settings.write_to_config()

    def _width_small_neg_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        galvo_settings.dslm_scan_width -= GalvoController.OFFSET_SMALL_STEP

        self._set_scanning_mode()
        self._update_dialog()
        galvo_settings.write_to_config()

    def _width_small_pos_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        galvo_settings.dslm_scan_width += GalvoController.OFFSET_SMALL_STEP

        self._set_scanning_mode()
        self._update_dialog()
        galvo_settings.write_to_config()

    def _width_big_pos_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        galvo_settings.dslm_scan_width += GalvoController.OFFSET_BIG_STEP

        self._set_scanning_mode()
        self._update_dialog()
        galvo_settings.write_to_config()

    def _set_lower_limit_button_clicked(self):
        # Sets lower limit of LSRM. Worth noting that lower_limit should be less than upper_limit,
        # even though lowering the offset makes the laser move up.
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        galvo_settings.lsrm_lower = galvo_settings.lsrm_cur_pos

        if self.galvo_dialog.scanning_check_box.isChecked():
            self._set_scanning_mode()
        self._update_dialog()
        galvo_settings.write_to_config()

    def _set_upper_limit_button_clicked(self):
        # Same as lower_limit but for upper limit. Value of upper limit should be greater than lower limit.
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        galvo_settings.lsrm_upper = galvo_settings.lsrm_cur_pos

        if self.galvo_dialog.scanning_check_box.isChecked():
            self._set_scanning_mode()
        self._update_dialog()
        galvo_settings.write_to_config()

    def _framerate_neg_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        galvo_settings.lsrm_framerate -= 1

        if self.galvo_dialog.scanning_check_box.isChecked():
            self._set_scanning_mode()
            # Chaning framerate also changes ILI, so camera must be updated.
            self._set_camera_properties()
        self._update_dialog()
        galvo_settings.write_to_config()

    def _framerate_pos_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        galvo_settings.lsrm_framerate += 1

        if self.galvo_dialog.scanning_check_box.isChecked():
            self._set_scanning_mode()
            self._set_camera_properties()
        self._update_dialog()
        galvo_settings.write_to_config()

    def _cam_delay_neg_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        galvo_settings.lsrm_cam_delay -= GalvoController.DELAY_STEP

        if self.galvo_dialog.scanning_check_box.isChecked():
            self._set_scanning_mode()
        self._update_dialog()
        galvo_settings.write_to_config()

    def _cam_delay_pos_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        galvo_settings.lsrm_cam_delay += GalvoController.DELAY_STEP

        if self.galvo_dialog.scanning_check_box.isChecked():
            self._set_scanning_mode()
        self._update_dialog()
        galvo_settings.write_to_config()

    def _laser_delay_neg_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        galvo_settings.lsrm_laser_delay -= GalvoController.DELAY_STEP

        if self.galvo_dialog.scanning_check_box.isChecked():
            self._set_scanning_mode()
        self._update_dialog()
        galvo_settings.write_to_config()

    def _laser_delay_pos_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        galvo_settings.lsrm_laser_delay += GalvoController.DELAY_STEP

        if self.galvo_dialog.scanning_check_box.isChecked():
            self._set_scanning_mode()
        self._update_dialog()
        galvo_settings.write_to_config()

    def _offset_line_edit_event(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            if self.galvo_dialog.offset_line_edit.hasAcceptableInput():
                offset = float(self.galvo_dialog.offset_line_edit.text())
                if self._lsrm_bool:
                    galvo_settings.lsrm_cur_pos = offset
                else:
                    galvo_settings.dslm_offset = offset

                self._set_scanning_mode()
                galvo_settings.write_to_config()
            else:
                self._update_dialog()

    def _width_line_edit_event(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            if self.galvo_dialog.width_line_edit.hasAcceptableInput():
                galvo_settings.dslm_scan_width = float(self.galvo_dialog.width_line_edit.text())

                self._set_scanning_mode()
                galvo_settings.write_to_config()
            else:
                self._update_dialog()

    def _focus_line_edit_event(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            if self.galvo_dialog.focus_line_edit.hasAcceptableInput():
                galvo_settings.focus = float(self.galvo_dialog.focus_line_edit.text())

                self._set_scanning_mode()
                galvo_settings.write_to_config()
            else:
                self._update_dialog()

    def _lsrm_lower_line_edit_event(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            if self.galvo_dialog.lsrm_lower_line_edit.hasAcceptableInput():
                galvo_settings.lsrm_lower = float(self.galvo_dialog.lsrm_lower_line_edit.text())

                if self.galvo_dialog.scanning_check_box.isChecked():
                    self._set_scanning_mode()
                galvo_settings.write_to_config()
            else:
                self._update_dialog()

    def _lsrm_upper_line_edit_event(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            if self.galvo_dialog.lsrm_upper_line_edit.hasAcceptableInput():
                galvo_settings.lsrm_upper = float(self.galvo_dialog.lsrm_upper_line_edit.text())

                if self.galvo_dialog.scanning_check_box.isChecked():
                    self._set_scanning_mode()
                galvo_settings.write_to_config()
            else:
                self._update_dialog()

    def _cam_delay_line_edit_event(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            if self.galvo_dialog.cam_delay_line_edit.hasAcceptableInput():
                galvo_settings.lsrm_cam_delay = float(self.galvo_dialog.cam_delay_line_edit.text())

                if self.galvo_dialog.scanning_check_box.isChecked():
                    self._set_scanning_mode()
                galvo_settings.write_to_config()
            else:
                self._update_dialog()

    def _laser_delay_line_edit_event(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            if self.galvo_dialog.laser_delay_line_edit.hasAcceptableInput():
                galvo_settings.lsrm_laser_delay = float(self.galvo_dialog.laser_delay_line_edit.text())

                if self.galvo_dialog.scanning_check_box.isChecked():
                    self._set_scanning_mode()
                galvo_settings.write_to_config()
            else:
                self._update_dialog()

    def _num_lines_line_edit_event(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            if self.galvo_dialog.num_lines_line_edit.hasAcceptableInput():
                galvo_settings.lsrm_num_lines = int(self.galvo_dialog.num_lines_line_edit.text())

                if self.galvo_dialog.scanning_check_box.isChecked():
                    self._set_scanning_mode()
                    self._set_camera_properties()
                galvo_settings.write_to_config()
            else:
                self._update_dialog()
