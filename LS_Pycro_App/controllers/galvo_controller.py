import contextlib
import logging
import sys

from PyQt5 import QtGui

from LS_Pycro_App.hardware import Galvo, Camera, Plc, exceptions
from LS_Pycro_App.views import GalvoDialog
from LS_Pycro_App.utils import general_functions


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
    _OFFSET_SMALL_STEP = 0.01
    _OFFSET_BIG_STEP = 0.1
    _FOCUS_SMALL_STEP = 0.001
    _FOCUS_BIG_STEP = 0.01
    _DELAY_STEP = .01
    _NUM_DECIMAL_PLACES = 3

    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)
        self.galvo_dialog = GalvoDialog()

        self._scan_mode_model = QtGui.QStandardItemModel()

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

        # Set validators and extra Galvo.settings
        validator = QtGui.QDoubleValidator()
        validator.setBottom(Galvo.settings.WIDTH_BOT_LIMIT)
        validator.setTop(Galvo.settings.WIDTH_TOP_LIMIT)
        validator.setDecimals(GalvoController._NUM_DECIMAL_PLACES)
        self.galvo_dialog.width_line_edit.setValidator(validator)

        validator = QtGui.QDoubleValidator()
        validator.setBottom(Galvo.settings.OFFSET_BOT_LIMIT)
        validator.setTop(Galvo.settings.OFFSET_TOP_LIMIT)
        validator.setDecimals(GalvoController._NUM_DECIMAL_PLACES)
        self.galvo_dialog.offset_line_edit.setValidator(validator)
        self.galvo_dialog.focus_line_edit.setValidator(validator)
        self.galvo_dialog.lsrm_lower_line_edit.setValidator(validator)
        self.galvo_dialog.lsrm_upper_line_edit.setValidator(validator)

        validator = QtGui.QDoubleValidator()
        validator.setBottom(Galvo.settings.DELAY_BOT_LIMIT)
        validator.setTop(Galvo.settings.DELAY_TOP_LIMIT)
        validator.setDecimals(GalvoController._NUM_DECIMAL_PLACES)
        self.galvo_dialog.cam_delay_line_edit.setValidator(validator)
        self.galvo_dialog.laser_delay_line_edit.setValidator(validator)

        validator = QtGui.QIntValidator()
        validator.setBottom(Galvo.settings.NUM_LINES_BOT_LIMIT)
        validator.setTop(Galvo.settings.NUM_LINES_TOP_LIMIT)
        self.galvo_dialog.num_lines_line_edit.setValidator(validator)

        self.galvo_dialog.framerate_line_edit.setReadOnly(True)

        # Initialize Galvo.settings and dialog values
        self._init_scan_mode_combo_box()
        self._update_dialog()
        self._set_scanning_mode()

    def _init_scan_mode_combo_box(self):
        self.galvo_dialog.scan_mode_combo_box.setModel(self._scan_mode_model)
        self._scan_mode_model.appendRow(QtGui.QStandardItem(GalvoController._DSLM_NAME))
        self._scan_mode_model.appendRow(QtGui.QStandardItem(GalvoController._LSRM_NAME))

    def _update_dialog(self):
        self._update_dialog_values()
        self._set_dialog_mode()

    # _update_dialog helpers
    def _update_dialog_values(self):
        """
        Updates all values in dialog to match current state of Galvo.settings.
        """
        self.galvo_dialog.width_line_edit.setText(general_functions.float_to_str(
            Galvo.settings.dslm_scan_width, self._NUM_DECIMAL_PLACES))
        self.galvo_dialog.focus_line_edit.setText(general_functions.float_to_str(
            Galvo.settings.focus, self._NUM_DECIMAL_PLACES))
        self.galvo_dialog.lsrm_lower_line_edit.setText(general_functions.float_to_str(
            Galvo.settings.lsrm_lower, self._NUM_DECIMAL_PLACES))
        self.galvo_dialog.lsrm_upper_line_edit.setText(general_functions.float_to_str(
            Galvo.settings.lsrm_upper, self._NUM_DECIMAL_PLACES))
        self.galvo_dialog.framerate_line_edit.setText(str(Galvo.settings.lsrm_framerate))
        self.galvo_dialog.cam_delay_line_edit.setText(general_functions.float_to_str(
            Galvo.settings.lsrm_cam_delay, self._NUM_DECIMAL_PLACES))
        self.galvo_dialog.laser_delay_line_edit.setText(general_functions.float_to_str(
            Galvo.settings.lsrm_laser_delay, self._NUM_DECIMAL_PLACES))
        self.galvo_dialog.num_lines_line_edit.setText(str(Galvo.settings.lsrm_num_lines))

        if Galvo.settings.is_lsrm:
            self.galvo_dialog.offset_line_edit.setText(general_functions.float_to_str(
                Galvo.settings.lsrm_cur_pos, self._NUM_DECIMAL_PLACES))
        else:
            self.galvo_dialog.offset_line_edit.setText(general_functions.float_to_str(
                Galvo.settings.dslm_offset, self._NUM_DECIMAL_PLACES))

    def _set_dialog_mode(self):
        """
        Switches between lsrm dialog mode and dslm dialog based on state of lsrm_bool. 
        """
        if Galvo.settings.is_lsrm:
            self.galvo_dialog.scan_mode_combo_box.setCurrentText(self._LSRM_NAME)
            self.galvo_dialog.offset_label.setText("Position")
            self.galvo_dialog.resize(438, 350)
        else:
            self.galvo_dialog.scan_mode_combo_box.setCurrentText(self._DSLM_NAME)
            self.galvo_dialog.offset_label.setText("Offset")
            self.galvo_dialog.resize(438, 140)

        self.galvo_dialog.width_label.setVisible(not Galvo.settings.is_lsrm)
        self.galvo_dialog.width_line_edit.setVisible(not Galvo.settings.is_lsrm)
        self.galvo_dialog.width_unit_label.setVisible(not Galvo.settings.is_lsrm)
        self.galvo_dialog.width_big_neg_button.setVisible(not Galvo.settings.is_lsrm)
        self.galvo_dialog.width_small_neg_button.setVisible(not Galvo.settings.is_lsrm)
        self.galvo_dialog.width_small_pos_button.setVisible(not Galvo.settings.is_lsrm)
        self.galvo_dialog.width_big_pos_button.setVisible(not Galvo.settings.is_lsrm)

        self.galvo_dialog.lsrm_lower_label.setVisible(Galvo.settings.is_lsrm)
        self.galvo_dialog.lsrm_lower_line_edit.setVisible(Galvo.settings.is_lsrm)
        self.galvo_dialog.lsrm_lower_unit_label.setVisible(Galvo.settings.is_lsrm)
        self.galvo_dialog.lsrm_set_lower_button.setVisible(Galvo.settings.is_lsrm)

        self.galvo_dialog.lsrm_upper_label.setVisible(Galvo.settings.is_lsrm)
        self.galvo_dialog.lsrm_upper_line_edit.setVisible(Galvo.settings.is_lsrm)
        self.galvo_dialog.lsrm_upper_unit_label.setVisible(Galvo.settings.is_lsrm)
        self.galvo_dialog.lsrm_set_upper_button.setVisible(Galvo.settings.is_lsrm)

        self.galvo_dialog.framerate_label.setVisible(Galvo.settings.is_lsrm)
        self.galvo_dialog.framerate_line_edit.setVisible(Galvo.settings.is_lsrm)
        self.galvo_dialog.framerate_unit_label.setVisible(Galvo.settings.is_lsrm)
        self.galvo_dialog.framerate_neg_button.setVisible(Galvo.settings.is_lsrm)
        self.galvo_dialog.framerate_pos_button.setVisible(Galvo.settings.is_lsrm)

        self.galvo_dialog.cam_delay_label.setVisible(Galvo.settings.is_lsrm)
        self.galvo_dialog.cam_delay_line_edit.setVisible(Galvo.settings.is_lsrm)
        self.galvo_dialog.cam_delay_unit_label.setVisible(Galvo.settings.is_lsrm)
        self.galvo_dialog.cam_delay_neg_button.setVisible(Galvo.settings.is_lsrm)
        self.galvo_dialog.cam_delay_pos_button.setVisible(Galvo.settings.is_lsrm)

        self.galvo_dialog.laser_delay_label.setVisible(Galvo.settings.is_lsrm)
        self.galvo_dialog.laser_delay_line_edit.setVisible(Galvo.settings.is_lsrm)
        self.galvo_dialog.laser_delay_unit_label.setVisible(Galvo.settings.is_lsrm)
        self.galvo_dialog.laser_delay_neg_button.setVisible(Galvo.settings.is_lsrm)
        self.galvo_dialog.laser_delay_pos_button.setVisible(Galvo.settings.is_lsrm)

        self.galvo_dialog.num_lines_label.setVisible(Galvo.settings.is_lsrm)
        self.galvo_dialog.num_lines_line_edit.setVisible(Galvo.settings.is_lsrm)

    def _set_scanning_mode(self):
        with contextlib.suppress(exceptions.HardwareException):
            if self.galvo_dialog.scanning_check_box.isChecked():
                if Galvo.settings.is_lsrm:
                    Plc.set_continuous_pulses(Galvo.settings.lsrm_framerate)
                    Galvo.set_lsrm_mode()
                else:
                    Galvo.set_dslm_mode()
            else:
                if Galvo.settings.is_lsrm:
                    Galvo.set_lsrm_alignment_mode()
                else:
                    Galvo.set_dslm_alignment_mode()

    def _scan_mode_combo_box_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        Galvo.settings.is_lsrm = self.galvo_dialog.scan_mode_combo_box.currentText() == GalvoController._LSRM_NAME
        self._set_scanning_mode()
        if self.galvo_dialog.scanning_check_box.isChecked():
            if Galvo.settings.is_lsrm:
                Camera.set_lsrm_mode(Galvo.settings.lsrm_ili, Galvo.settings.lsrm_num_lines)
            else:
                Camera.set_burst_mode()
                Camera.set_exposure(Camera.DEFAULT_EXPOSURE)
        Camera.start_live_acquisition()
        self._update_dialog()
        Galvo.settings.write_to_config()

    def _scanning_check_box_stage_changed(self):
        # If checked, starts laser scanning
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        if self.galvo_dialog.scanning_check_box.isChecked():
            if Galvo.settings.is_lsrm:
                Camera.set_lsrm_mode(Galvo.settings.lsrm_ili, Galvo.settings.lsrm_num_lines)
        elif Galvo.settings.is_lsrm:
            Camera.set_burst_mode()
            Camera.set_exposure(Camera.DEFAULT_EXPOSURE)
        Camera.start_live_acquisition()
        self._set_scanning_mode()

    def _offset_big_neg_button_clicked(self):
        # Since offset line edit acts as both offset for continuous_scan and
        # current position for lsrm, some extra logic is needed to ensure it's
        # changing the correct attributes.
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        if Galvo.settings.is_lsrm:
            Galvo.settings.lsrm_cur_pos -= GalvoController._OFFSET_BIG_STEP
        else:
            Galvo.settings.dslm_offset -= GalvoController._OFFSET_BIG_STEP

        self._set_scanning_mode()
        self._update_dialog()
        Galvo.settings.write_to_config()

    def _offset_small_neg_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        if Galvo.settings.is_lsrm:
            Galvo.settings.lsrm_cur_pos -= GalvoController._OFFSET_SMALL_STEP
        else:
            Galvo.settings.dslm_offset -= GalvoController._OFFSET_SMALL_STEP

        self._set_scanning_mode()
        self._update_dialog()
        Galvo.settings.write_to_config()

    def _offset_small_pos_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        if Galvo.settings.is_lsrm:
            Galvo.settings.lsrm_cur_pos += GalvoController._OFFSET_SMALL_STEP
        else:
            Galvo.settings.dslm_offset += GalvoController._OFFSET_SMALL_STEP

        self._set_scanning_mode()
        self._update_dialog()
        Galvo.settings.write_to_config()

    def _offset_big_pos_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        if Galvo.settings.is_lsrm:
            Galvo.settings.lsrm_cur_pos += GalvoController._OFFSET_BIG_STEP
        else:
            Galvo.settings.dslm_offset += GalvoController._OFFSET_BIG_STEP

        self._set_scanning_mode()
        self._update_dialog()
        Galvo.settings.write_to_config()

    def _focus_big_neg_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        Galvo.settings.focus -= GalvoController._FOCUS_BIG_STEP

        self._set_scanning_mode()
        self._update_dialog()
        Galvo.settings.write_to_config()

    def _focus_small_neg_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        Galvo.settings.focus -= GalvoController._FOCUS_SMALL_STEP

        self._set_scanning_mode()
        self._update_dialog()
        Galvo.settings.write_to_config()

    def _focus_small_pos_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        Galvo.settings.focus += GalvoController._FOCUS_SMALL_STEP

        self._set_scanning_mode()
        self._update_dialog()
        Galvo.settings.write_to_config()

    def _focus_big_pos_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        Galvo.settings.focus += GalvoController._FOCUS_BIG_STEP

        self._set_scanning_mode()
        self._update_dialog()
        Galvo.settings.write_to_config()

    def _width_big_neg_button_clicked(self):
        # Changes scanning range of galvo. Currently, 1.100mV scans
        # the entire camera field.
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        Galvo.settings.dslm_scan_width -= GalvoController._OFFSET_BIG_STEP

        self._set_scanning_mode()
        self._update_dialog()
        Galvo.settings.write_to_config()

    def _width_small_neg_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        Galvo.settings.dslm_scan_width -= GalvoController._OFFSET_SMALL_STEP

        self._set_scanning_mode()
        self._update_dialog()
        Galvo.settings.write_to_config()

    def _width_small_pos_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        Galvo.settings.dslm_scan_width += GalvoController._OFFSET_SMALL_STEP

        self._set_scanning_mode()
        self._update_dialog()
        Galvo.settings.write_to_config()

    def _width_big_pos_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        Galvo.settings.dslm_scan_width += GalvoController._OFFSET_BIG_STEP

        self._set_scanning_mode()
        self._update_dialog()
        Galvo.settings.write_to_config()

    def _set_lower_limit_button_clicked(self):
        # Sets lower limit of LSRM. Worth noting that lower_limit should be less than upper_limit,
        # even though lowering the offset makes the laser move up.
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        Galvo.settings.lsrm_lower = Galvo.settings.lsrm_cur_pos

        if self.galvo_dialog.scanning_check_box.isChecked():
            self._set_scanning_mode()
        self._update_dialog()
        Galvo.settings.write_to_config()

    def _set_upper_limit_button_clicked(self):
        # Same as lower_limit but for upper limit. Value of upper limit should be greater than lower limit.
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        Galvo.settings.lsrm_upper = Galvo.settings.lsrm_cur_pos

        if self.galvo_dialog.scanning_check_box.isChecked():
            self._set_scanning_mode()
        self._update_dialog()
        Galvo.settings.write_to_config()

    def _framerate_neg_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        Galvo.settings.lsrm_framerate -= 1

        if self.galvo_dialog.scanning_check_box.isChecked():
            self._set_scanning_mode()
            # Chaning framerate also changes ILI, so camera must be updated.
            Camera.set_lsrm_mode(Galvo.settings.lsrm_ili, Galvo.settings.lsrm_num_lines)
        self._update_dialog()
        Galvo.settings.write_to_config()

    def _framerate_pos_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        Galvo.settings.lsrm_framerate += 1

        if self.galvo_dialog.scanning_check_box.isChecked():
            self._set_scanning_mode()
            Camera.set_lsrm_mode(Galvo.settings.lsrm_ili, Galvo.settings.lsrm_num_lines)
        self._update_dialog()
        Galvo.settings.write_to_config()

    def _cam_delay_neg_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        Galvo.settings.lsrm_cam_delay -= GalvoController._DELAY_STEP

        if self.galvo_dialog.scanning_check_box.isChecked():
            self._set_scanning_mode()
        self._update_dialog()
        Galvo.settings.write_to_config()

    def _cam_delay_pos_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        Galvo.settings.lsrm_cam_delay += GalvoController._DELAY_STEP

        if self.galvo_dialog.scanning_check_box.isChecked():
            self._set_scanning_mode()
        self._update_dialog()
        Galvo.settings.write_to_config()

    def _laser_delay_neg_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        Galvo.settings.lsrm_laser_delay -= GalvoController._DELAY_STEP

        if self.galvo_dialog.scanning_check_box.isChecked():
            self._set_scanning_mode()
        self._update_dialog()
        Galvo.settings.write_to_config()

    def _laser_delay_pos_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        Galvo.settings.lsrm_laser_delay += GalvoController._DELAY_STEP

        if self.galvo_dialog.scanning_check_box.isChecked():
            self._set_scanning_mode()
        self._update_dialog()
        Galvo.settings.write_to_config()

    def _offset_line_edit_event(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):  
            if self.galvo_dialog.offset_line_edit.hasAcceptableInput():
                offset = float(self.galvo_dialog.offset_line_edit.text())
                if Galvo.settings.is_lsrm:
                    Galvo.settings.lsrm_cur_pos = offset
                else:
                    Galvo.settings.dslm_offset = offset

                self._set_scanning_mode()
                Galvo.settings.write_to_config()
            else:
                self._update_dialog()

    def _width_line_edit_event(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            if self.galvo_dialog.width_line_edit.hasAcceptableInput():
                Galvo.settings.dslm_scan_width = float(self.galvo_dialog.width_line_edit.text())

                self._set_scanning_mode()
                Galvo.settings.write_to_config()
            else:
                self._update_dialog()

    def _focus_line_edit_event(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            if self.galvo_dialog.focus_line_edit.hasAcceptableInput():
                Galvo.settings.focus = float(self.galvo_dialog.focus_line_edit.text())

                self._set_scanning_mode()
                Galvo.settings.write_to_config()
            else:
                self._update_dialog()

    def _lsrm_lower_line_edit_event(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            if self.galvo_dialog.lsrm_lower_line_edit.hasAcceptableInput():
                Galvo.settings.lsrm_lower = float(self.galvo_dialog.lsrm_lower_line_edit.text())

                if self.galvo_dialog.scanning_check_box.isChecked():
                    self._set_scanning_mode()
                Galvo.settings.write_to_config()
            else:
                self._update_dialog()

    def _lsrm_upper_line_edit_event(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            if self.galvo_dialog.lsrm_upper_line_edit.hasAcceptableInput():
                Galvo.settings.lsrm_upper = float(self.galvo_dialog.lsrm_upper_line_edit.text())

                if self.galvo_dialog.scanning_check_box.isChecked():
                    self._set_scanning_mode()
                Galvo.settings.write_to_config()
            else:
                self._update_dialog()

    def _cam_delay_line_edit_event(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            if self.galvo_dialog.cam_delay_line_edit.hasAcceptableInput():
                Galvo.settings.lsrm_cam_delay = float(self.galvo_dialog.cam_delay_line_edit.text())

                if self.galvo_dialog.scanning_check_box.isChecked():
                    self._set_scanning_mode()
                Galvo.settings.write_to_config()
            else:
                self._update_dialog()

    def _laser_delay_line_edit_event(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            if self.galvo_dialog.laser_delay_line_edit.hasAcceptableInput():
                Galvo.settings.lsrm_laser_delay = float(self.galvo_dialog.laser_delay_line_edit.text())

                if self.galvo_dialog.scanning_check_box.isChecked():
                    self._set_scanning_mode()
                Galvo.settings.write_to_config()
            else:
                self._update_dialog()

    def _num_lines_line_edit_event(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            if self.galvo_dialog.num_lines_line_edit.hasAcceptableInput():
                Galvo.settings.lsrm_num_lines = int(self.galvo_dialog.num_lines_line_edit.text())

                if self.galvo_dialog.scanning_check_box.isChecked():
                    self._set_scanning_mode()
                    Camera.set_lsrm_mode(Galvo.settings.lsrm_ili, Galvo.settings.lsrm_num_lines)
                Galvo.settings.write_to_config()
            else:
                self._update_dialog()
