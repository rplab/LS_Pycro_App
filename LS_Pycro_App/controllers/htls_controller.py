import contextlib
import logging
import sys
from copy import deepcopy
from pathlib import Path

from PyQt5 import QtGui, QtWidgets

from LS_Pycro_App.acquisition.acq_gui import HTLSAcqGui
from LS_Pycro_App.acquisition.main import HTLSAcquisition
from LS_Pycro_App.models.acq_settings import HTLSSettings
from LS_Pycro_App.hardware import Stage, Camera
from LS_Pycro_App.hardware.camera import Hamamatsu
from LS_Pycro_App.models.acq_settings import Region
from LS_Pycro_App.models.acq_directory import AcqDirectory
from LS_Pycro_App.views import BrowseDialog, HTLSAcqRegionsDialog, HTLSAcqSettingsDialog, HTLSAdvSettingsDialog, HTLSAcqDialog, AbortDialog
from LS_Pycro_App.utils import exceptions


class HTLSController(object):
    """
    This is the controller of the acquisition module. The main model is the AcqSettings class and the
    view is  AcquisitionRegionsDialog (and AcquisitionDialog). This class controls
    the gui value display and logic, and controls an instance of AcqSettings
    to hold data from user input. 

    In addition, it starts the image acquisition through the Thread inherited start() method
    in the Acquisition class.

    ## Design Notes

    This class uses a pseudo-pointer system to keep track of and update the correct instances of Fish
    and Region. self._fish and self._region are assigned to elements in self._acq_settings.fish_list 
    and fish.region_list through the use of fish_num and region_num indexes. Since lists are mutable,
    changing self._fish after assigning it to an element in acq_settings.fish_list will change
    the element itself (it's a reference to the same object).

    If an element doesn't exist at the index specified by fish_num or region_num, a new instance is
    created at self._fish or self._region, but is not immediately initialized to fish_list or region_list. 
    New elements are only initialized in their respective list when either the set region or paste region 
    button is pressed by the user. This is to prevent unwanted/empty regions from being initialized.

    ## Future Changes:

    - This is by far the most boilerplatey/gross file in the whole application. Main way to fix this 
    is to find a better way to connect PyQt5 buttons to methods.

    - Color code table so that regions from the same fish are the same color
    """
    
    NUM_DECIMAL_PLACES = 3

    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)
        self.regions_dialog = HTLSAcqRegionsDialog()
        self._acq_dialog = HTLSAcqDialog()
        self._acq_settings_dialog = HTLSAcqSettingsDialog()
        self._adv_settings_dialog = HTLSAdvSettingsDialog()
        self._htls_settings = HTLSSettings()
        self._acq_settings = self._htls_settings.acq_settings
        self._adv_settings = self._acq_settings.adv_settings

        self._fish = self._htls_settings.fish_settings
        self._region_num = 0
        self._region = Region()

        self._set_widget_models()
        self._set_validators()
        self._connect_signals()
        self._set_additional_widget_settings()
        self._update_dialogs()
    
    def _set_widget_models(self):
         # initialize item (list) models
        self._region_table_model = QtGui.QStandardItemModel()
        self._z_stack_available_model = QtGui.QStandardItemModel()
        self._z_stack_used_model = QtGui.QStandardItemModel()
        self._snap_available_model = QtGui.QStandardItemModel()
        self._snap_used_model = QtGui.QStandardItemModel()
        self._video_available_model = QtGui.QStandardItemModel()
        self._video_used_model = QtGui.QStandardItemModel()
        self._channel_order_model = QtGui.QStandardItemModel()
        self._speed_list_model = QtGui.QStandardItemModel()
        self._acq_order_model = QtGui.QStandardItemModel()

        self.regions_dialog.region_table_view.setModel(self._region_table_model)
        self.regions_dialog.z_stack_available_list_view.setModel(self._z_stack_available_model)
        self.regions_dialog.z_stack_used_list_view.setModel(self._z_stack_used_model)
        self.regions_dialog.snap_available_list_view.setModel(self._snap_available_model)
        self.regions_dialog.snap_used_list_view.setModel(self._snap_used_model)
        self.regions_dialog.video_available_list_view.setModel(self._video_available_model)
        self.regions_dialog.video_used_list_view.setModel(self._video_used_model)
        self._acq_settings_dialog.channel_order_list_view.setModel(self._channel_order_model)
        self._adv_settings_dialog.stage_speed_combo_box.setModel(self._speed_list_model)


        # uses core channel list to initialize list model values
        for channel in self._acq_settings.core_channel_list:
            self._z_stack_available_model.appendRow(QtGui.QStandardItem(channel))
            self._snap_available_model.appendRow(QtGui.QStandardItem(channel))
            self._video_available_model.appendRow(QtGui.QStandardItem(channel))

        for speed in self._adv_settings.speed_list:
            item = QtGui.QStandardItem(str(speed))
            self._speed_list_model.appendRow(item)
        self._adv_settings_dialog.stage_speed_combo_box.setCurrentText(str(self._adv_settings.z_stack_stage_speed))


    def _set_validators(self):
        # Validators and extra properties
        validator = QtGui.QIntValidator()
        self.regions_dialog.start_x_line_edit.setValidator(validator)
        self.regions_dialog.start_y_line_edit.setValidator(validator)
        self.regions_dialog.start_z_line_edit.setValidator(validator)

        validator = QtGui.QIntValidator()
        validator.setBottom(1)
        self.regions_dialog.step_size_line_edit.setValidator(validator)
        self.regions_dialog.video_num_frames_line_edit.setValidator(validator)

        validator = QtGui.QDoubleValidator()
        validator.setDecimals(HTLSController.NUM_DECIMAL_PLACES)
        validator.setBottom(Camera.MIN_EXPOSURE)
        validator.setTop(Camera.MAX_EXPOSURE)
        self.regions_dialog.snap_exposure_line_edit.setValidator(validator)
        self.regions_dialog.video_exposure_line_edit.setValidator(validator)
    
    def _connect_signals(self):
        # Initialize AcquisitionRegionsDialog event handlers. Organized by where they show up in the GUI.
        # TODO find a less ugly/more automated way of doing this. Yikes.
        self.regions_dialog.start_go_to_button.clicked.connect(self.start_go_to_button_clicked)
        self.regions_dialog.start_set_position_button.clicked.connect(self._start_set_position_button_clicked)
        self.regions_dialog.start_x_line_edit.textEdited.connect(self._start_x_line_edit_event)
        self.regions_dialog.start_y_line_edit.textEdited.connect(self._start_y_line_edit_event)
        self.regions_dialog.start_z_line_edit.textEdited.connect(self._start_z_line_edit_event)

        self.regions_dialog.num_fish_line_edit.textEdited.connect(self.num_fish_line_edit_event)
        self.regions_dialog.fish_type_line_edit.textEdited.connect(self._fish_type_line_edit_event)
        self.regions_dialog.age_line_edit.textEdited.connect(self._age_line_edit_event)
        self.regions_dialog.treatment_line_edit.textEdited.connect(self._treatment_line_edit_event)
        self.regions_dialog.add_notes_text_edit.textChanged.connect(self._add_notes_text_edit_event)

        self.regions_dialog.prev_region_button.clicked.connect(self._prev_region_button_clicked)
        self.regions_dialog.remove_region_button.clicked.connect(self._remove_region_button_clicked)
        self.regions_dialog.add_region_button.clicked.connect(self._add_region_button_clicked)
        self.regions_dialog.next_region_button.clicked.connect(self._next_region_button_clicked)

        self.regions_dialog.z_stack_check_box.clicked.connect(self._z_stack_check_clicked)
        self.regions_dialog.step_size_line_edit.textEdited.connect(self._step_size_line_edit_event)
        self.regions_dialog.z_stack_available_list_view.doubleClicked.connect(self._z_stack_available_list_move)
        self.regions_dialog.z_stack_used_list_view.doubleClicked.connect(self._z_stack_used_list_move)

        self.regions_dialog.snap_check_box.clicked.connect(self._snap_check_clicked)
        self.regions_dialog.snap_exposure_line_edit.textEdited.connect(self._snap_exposure_line_edit_event)
        self.regions_dialog.snap_available_list_view.doubleClicked.connect(self._snap_available_list_move)
        self.regions_dialog.snap_used_list_view.doubleClicked.connect(self._snap_used_list_move)

        self.regions_dialog.video_check_box.clicked.connect(self._video_check_clicked)
        self.regions_dialog.video_num_frames_line_edit.textEdited.connect(self._video_num_frames_line_edit_event)
        self.regions_dialog.video_exposure_line_edit.textEdited.connect(self._video_exposure_line_edit_event)
        self.regions_dialog.video_available_list_view.doubleClicked.connect(self._video_available_list_move)
        self.regions_dialog.video_used_list_view.doubleClicked.connect(self._video_used_list_move)

        self.regions_dialog.acq_setup_button.clicked.connect(self._acq_setup_button_clicked)
        self.regions_dialog.reset_joystick_button.clicked.connect(self._reset_joystick_button_clicked)

        # Initialize AcqSettingsDialog event handlers
        self._acq_settings_dialog.channel_order_move_up_button.clicked.connect(self._channel_move_up_button_clicked)
        self._acq_settings_dialog.channel_order_move_down_button.clicked.connect(self._channel_move_down_button_clicked)

        self._acq_settings_dialog.adv_settings_button.clicked.connect(self._adv_settings_button_clicked)

        self._acq_settings_dialog.browse_button.clicked.connect(self._browse_button_clicked)
        self._acq_settings_dialog.save_path_line_edit.textEdited.connect(self._save_path_line_edit_event)
        self._acq_settings_dialog.researcher_line_edit.textEdited.connect(self._researcher_line_edit_event)
        self._acq_settings_dialog.start_acquisition_button.clicked.connect(self._start_acquisition_button_clicked)
        self._acq_settings_dialog.show_acquisition_dialog_button.clicked.connect(self._show_acquisition_dialog_button_clicked)

        # Initialize AdvancedSettingsDialog event handlers
        self._adv_settings_dialog.z_stack_spectral_check_box.clicked.connect(self._z_stack_spectral_check_clicked)
        self._adv_settings_dialog.stage_speed_combo_box.activated.connect(self._stage_speed_combo_box_clicked)
        self._adv_settings_dialog.custom_exposure_check_box.clicked.connect(self._custom_exposure_check_box_clicked)
        self._adv_settings_dialog.z_stack_exposure_line_edit.textEdited.connect(self._z_stack_exposure_line_edit_event)

        self._adv_settings_dialog.lsrm_check_box.clicked.connect(self._lsrm_check_box_clicked)

        self._adv_settings_dialog.video_spectral_check_box.clicked.connect(self._video_spectral_check_clicked)

        self._adv_settings_dialog.backup_directory_check_box.clicked.connect(self._backup_directory_check_clicked)
        self._adv_settings_dialog.backup_directory_browse_button.clicked.connect(self._second_browse_button_clicked)
        self._adv_settings_dialog.backup_directory_line_edit.textEdited.connect(self._backup_directory_line_edit_event)

        self._adv_settings_dialog.end_videos_check_box.clicked.connect(self._end_videos_check_box_clicked)
        self._adv_settings_dialog.end_videos_num_frames_line_edit.textEdited.connect(self._end_videos_num_frames_line_edit_event)
        self._adv_settings_dialog.end_videos_exposure_line_edit.textEdited.connect(self._end_videos_exposure_line_edit)

    def _set_additional_widget_settings(self):
        self._acq_settings_dialog.channel_order_list_view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.regions_dialog.region_table_view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        #custom exposure should always be allowed on WIL and lsrm isn't supported.
        is_hamamatsu = Camera is Hamamatsu
        self._adv_settings_dialog.custom_exposure_check_box.setVisible(is_hamamatsu)
        self._adv_settings_dialog.z_stack_exposure_line_edit.setEnabled(not is_hamamatsu)
        self._adv_settings_dialog.lsrm_check_box.setEnabled(is_hamamatsu)

    def _update_dialogs(self):
        """
        updatees all dialogs to match model. 

        Most of the time, all of these are called together. However, there are cases where certain
        GUI elements updating can mess with GUI interactions, and so in those cases, only a selection
        of these functions are called.
        """
        #acq_settings.update() doesn't quite fit in with other update methods, since this is actually an update 
        #of the model based on settings in model and core, but this should be called frequently anyway and it seems
        #like a decent spot or it.
        self._update_regions_dialog()
        self._update_region_table()
        self._update_acq_settings_dialog()
        self._update_adv_settings_dialog()
        self._htls_settings.write_to_config()

    def _update_acq_settings_dialog(self):
        """
        Updates all GUI elements (in PyQt5, widgets) of acq_settings_dialog to reflect the 
        current values in acq_settings
        """
        self._update_channel_order_model()
        self._update_save_path_widgets()

    # _update_acq_settings_dialog helpers
    def _update_channel_order_model(self):
        self._channel_order_model.clear()
        for channel in self._acq_settings.channel_order_list:
            self._channel_order_model.appendRow(QtGui.QStandardItem(channel))

    def _update_save_path_widgets(self):
        self._acq_settings_dialog.save_path_line_edit.setText(self._acq_settings.directory)
        self._acq_settings_dialog.researcher_line_edit.setText(self._acq_settings.researcher)

    def _update_adv_settings_dialog(self):
        self._update_adv_z_stack_widgets()
        self._update_adv_video_widgets()
        self._update_adv_backup_directory_widgets()
        self._update_end_videos_widgets()

    # update_adv_settings_dialog helpers
    def _update_adv_z_stack_widgets(self):
        self._adv_settings_dialog.z_stack_spectral_check_box.setChecked(self._adv_settings.spectral_z_stack_enabled)
        self._adv_settings_dialog.stage_speed_combo_box.setCurrentText(str(self._adv_settings.z_stack_stage_speed))
        self._adv_settings_dialog.z_stack_exposure_line_edit.setText(str(self._adv_settings.z_stack_exposure))
        self._adv_settings_dialog.z_stack_exposure_line_edit.setEnabled(self._adv_settings_dialog.custom_exposure_check_box.isChecked())

    def _update_adv_video_widgets(self):
        self._adv_settings_dialog.video_spectral_check_box.setChecked(self._adv_settings.spectral_video_enabled)

    def _update_adv_backup_directory_widgets(self):
        self._adv_settings_dialog.backup_directory_check_box.setChecked(self._adv_settings.backup_directory_enabled)
        self._adv_settings_dialog.backup_directory_browse_button.setEnabled(self._adv_settings.backup_directory_enabled)
        self._adv_settings_dialog.backup_directory_line_edit.setEnabled(self._adv_settings.backup_directory_enabled)
        self._adv_settings_dialog.backup_directory_line_edit.setText(self._adv_settings.backup_directory)

    def _update_end_videos_widgets(self):
        self._adv_settings_dialog.end_videos_check_box.setChecked(self._adv_settings.end_videos_enabled)
        self._adv_settings_dialog.end_videos_num_frames_line_edit.setEnabled(self._adv_settings.end_videos_enabled)
        self._adv_settings_dialog.end_videos_num_frames_line_edit.setText(str(self._adv_settings.end_videos_num_frames))
        self._adv_settings_dialog.end_videos_exposure_line_edit.setEnabled(self._adv_settings.end_videos_enabled)
        self._adv_settings_dialog.end_videos_exposure_line_edit.setText(str(self._adv_settings.end_videos_exposure))

    def _update_regions_dialog(self):
        """
        Updates all GUI elements of AcquisitionRegionsDialog to reflect the values in the acq_settings
        fish list.

        First, self._fish and self._region pointers to elements specified by self._fish_num and self._region_num. 
        Then, updates all button states and line edits to match current intanes of fish and region.
        """
        region_bool = self._update_region()
        self._region_widgets_update(region_bool)
        self._fish_notes_update()
        self._position_widgets_update()

        self._region_z_stack_widgets_update()
        self._region_snap_widgets_update()
        self._region_video_widgets_update()

        # Sets the list models to reflect channel list in current region instance
        self._update_channel_list_models(
            self._z_stack_used_model, self._z_stack_available_model, self._region.z_stack_channel_list)
        self._update_channel_list_models(
            self._snap_used_model, self._snap_available_model, self._region.snap_channel_list)
        self._update_channel_list_models(
            self._video_used_model, self._video_available_model, self._region.video_channel_list)

    # _update_regions_dialog helpers
    def _update_region(self):
        region_found = False
        try:
            self._region = self._fish.region_list[self._region_num]
            region_found = True
        except IndexError:
            self._region = Region()
        return region_found

    def _region_widgets_update(self, region_bool):
        """
        Updates region buttons 

        If region_bool == True, remove region, next region, and go to are enabled. Else, disabled.

        If self._region_num > 0, previous region button is enabled. Else, disabled.
        """
        self.regions_dialog.region_label.setText(f"Region {self._region_num + 1}")
        self.regions_dialog.next_region_button.setEnabled(region_bool)
        self.regions_dialog.remove_region_button.setEnabled(region_bool)
        self.regions_dialog.prev_region_button.setEnabled(self._region_num > 0)

    def _fish_notes_update(self):
        self.regions_dialog.num_fish_line_edit.setText(str(self._htls_settings.num_fish))
        self.regions_dialog.fish_type_line_edit.setText(str(self._fish.fish_type))
        self.regions_dialog.age_line_edit.setText(str(self._fish.age))
        self.regions_dialog.treatment_line_edit.setText(str(self._fish.treatment))
        self.regions_dialog.add_notes_text_edit.setPlainText(str(self._fish.add_notes))

    def _position_widgets_update(self):
        self.regions_dialog.start_x_line_edit.setText(str(self._htls_settings.start_pos[0]))
        self.regions_dialog.start_y_line_edit.setText(str(self._htls_settings.start_pos[1]))
        self.regions_dialog.start_z_line_edit.setText(str(self._htls_settings.start_pos[2]))

    def _region_z_stack_widgets_update(self):
        """
        Updates all QtWidgets related to z_stack settings in regions_dialog.
        """
        z_stack_enabled = self._region.z_stack_enabled
        self.regions_dialog.z_stack_check_box.setChecked(z_stack_enabled)
        self.regions_dialog.step_size_line_edit.setEnabled(z_stack_enabled)
        self.regions_dialog.step_size_line_edit.setText(str(self._region.z_stack_step_size))
        self.regions_dialog.z_stack_available_list_view.setEnabled(z_stack_enabled)
        self.regions_dialog.z_stack_used_list_view.setEnabled(z_stack_enabled)

    def _region_snap_widgets_update(self):
        """
        Updates all QtWidgets related to snap settings in regions_dialog.
        """
        snap_enabled = self._region.snap_enabled
        self.regions_dialog.snap_check_box.setChecked(snap_enabled)
        self.regions_dialog.snap_exposure_line_edit.setEnabled(snap_enabled)
        self.regions_dialog.snap_exposure_line_edit.setText(str(self._region.snap_exposure))
        self.regions_dialog.snap_available_list_view.setEnabled(snap_enabled)
        self.regions_dialog.snap_used_list_view.setEnabled(snap_enabled)

    def _region_video_widgets_update(self):
        """
        Updates all QtWidgets related to video settings in regions_dialog.
        """
        video_enabled = self._region.video_enabled
        self.regions_dialog.video_check_box.setChecked(video_enabled)
        self.regions_dialog.video_num_frames_line_edit.setEnabled(video_enabled)
        self.regions_dialog.video_num_frames_line_edit.setText(str(self._region.video_num_frames))
        self.regions_dialog.video_exposure_line_edit.setEnabled(video_enabled)
        self.regions_dialog.video_exposure_line_edit.setText(str(self._region.video_exposure))
        self.regions_dialog.video_available_list_view.setEnabled(video_enabled)
        self.regions_dialog.video_used_list_view.setEnabled(video_enabled)

    def _update_channel_list_models(self, used_model:QtGui.QStandardItemModel, available_model:QtGui.QStandardItemModel, channel_list):
        used_model.clear()
        available_model.clear()
        for channel in channel_list:
            used_model.appendRow(QtGui.QStandardItem(channel))
        for channel in self._acq_settings.core_channel_list:
            if channel not in channel_list:
                available_model.appendRow(QtGui.QStandardItem(channel))

    def _update_region_table(self):
        """
        Sets the table to display values in current region_list within
        acquistiion_settings.

        #TODO make this not as disgusting. Perhaps find a way to automatically set headers
        based on attributes names. Only problem is attribute names are long. Maybe just use 
        small font? Wrapping headers? idk but this is awful.
        """
        self._region_table_model.clear()
        headers = ["reg #", 
                   "z stack",
                   "step", 
                   "chans", 
                   "snap", 
                   "exp", 
                   "chans", 
                   "video",
                   "frames", 
                   "exp", 
                   "chans"]
        self._region_table_model.setHorizontalHeaderLabels(headers)
        for region_num, region in enumerate(self._fish.region_list):
            row_list = [str(region_num + 1),
                        str(region.z_stack_enabled),
                        str(region.z_stack_step_size), 
                        ','.join(region.z_stack_channel_list),
                        str(region.snap_enabled), 
                        str(region.snap_exposure),
                        ','.join(region.snap_channel_list), 
                        str(region.video_enabled),
                        str(region.video_num_frames), 
                        str(region.video_exposure),
                        ','.join(region.video_channel_list)]
            row_list = [QtGui.QStandardItem(element) for element in row_list]
            self._region_table_model.appendRow(row_list)
        self.regions_dialog.region_table_view.resizeColumnsToContents()

    def start_go_to_button_clicked(self):
        # Goes to position set in current instance of Region
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        x_pos = self._htls_settings.start_pos[0]
        y_pos = self._htls_settings.start_pos[1]
        z_pos = self._htls_settings.start_pos[2]
        if None not in (x_pos, y_pos, z_pos):
            with contextlib.suppress(exceptions.HardwareException):
                Stage.move_stage(x_pos, y_pos, z_pos)
        self._update_dialogs()

    def _start_set_position_button_clicked(self):
        # Gets current stage position and creates element of region_list
        # with current settings in GUI. Currently, this method and the paste_regionButton
        # are the only ways to initialize an element in the region_list.
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        x_pos, y_pos, z_pos = None, None, None
        with contextlib.suppress(exceptions.HardwareException):
            x_pos = Stage.get_x_position()
            y_pos = Stage.get_y_position()
            z_pos = Stage.get_z_position()
        if None not in (x_pos, y_pos, z_pos):
            self._htls_settings.start_pos = [x_pos, y_pos, z_pos]
        else:
            message = "Region cannot be set. Stage failed to return position."
            self._logger.info(message)
            print(message)
        self._update_dialogs()

    def _prev_region_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._region_num -= 1
        self._update_dialogs()

    def _remove_region_button_clicked(self):
        # Removes current region from region_list.
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._fish.remove_region(self._region_num)
        self._update_dialogs()

    def _add_region_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._fish.append_blank_region()
        self._update_dialogs()

    def _next_region_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._region_num += 1
        self._update_dialogs()

    def _paste_button_clicked(self):
        # Initializes new region at current index with values from region_copy.
        # Currently the only method other than set_region_button_clicked to
        # initialize region in region_list.
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._region = deepcopy(self._region_copy)
        self._fish.update_region_list(self._region_num, self._region)
        self._update_dialogs()

    def _acq_setup_button_clicked(self):
        # Brings up acquisition settings dialog
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._acq_settings_dialog.show()
        self._acq_settings_dialog.activateWindow()

    def _reset_joystick_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(exceptions.HardwareException):
            Stage.reset_joystick()

    def _z_stack_check_clicked(self):
        # Enables/disables z_stack GUI elements when checkbox is clicked.
        # Also sets z_stack_enabled in region.
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        z_stack_enabled = self.regions_dialog.z_stack_check_box.isChecked()
        self._region.z_stack_enabled = z_stack_enabled
        self._update_dialogs()

    def _snap_check_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        snap_enabled = self.regions_dialog.snap_check_box.isChecked()
        self._region.snap_enabled = snap_enabled
        self._update_dialogs()

    def _video_check_clicked(self):
        # Same as z_stack_check_clicked but for video
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        video_enabled = self.regions_dialog.video_check_box.isChecked()
        self._region.video_enabled = video_enabled
        self._update_dialogs()

    def _list_move(self, 
                   list_view: QtWidgets.QListView, 
                   remove_model: QtGui.QStandardItemModel, 
                   add_model: QtGui.QStandardItemModel):
        channel_index = list_view.selectedIndexes()[0].row()
        channel = remove_model.item(channel_index).text()
        remove_model.removeRow(channel_index)
        add_model.appendRow(QtGui.QStandardItem(channel))
    
    def _get_list_from_model(self, model: QtGui.QStandardItemModel):
        lst = []
        for row in range(model.rowCount()):
            lst.append(model.item(row).text())
        return lst

    def _z_stack_available_list_move(self):
        # on double click, switches channel from available list to used list
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._list_move(self.regions_dialog.z_stack_available_list_view,
                        self._z_stack_available_model,
                        self._z_stack_used_model)
        self._region.z_stack_channel_list = self._get_list_from_model(self._z_stack_used_model)
        self._update_dialogs()

    def _z_stack_used_list_move(self):
        # Same as available_list_move except from used list to available list
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._list_move(self.regions_dialog.z_stack_used_list_view,
                        self._z_stack_used_model,
                        self._z_stack_available_model)
        self._region.z_stack_channel_list = self._get_list_from_model(self._z_stack_used_model)
        self._update_dialogs()

    def _snap_available_list_move(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._list_move(self.regions_dialog.snap_available_list_view,
                        self._snap_available_model,
                        self._snap_used_model)
        self._region.snap_channel_list = self._get_list_from_model(self._snap_used_model)
        self._update_dialogs()

    def _snap_used_list_move(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._list_move(self.regions_dialog.snap_used_list_view,
                        self._snap_used_model,
                        self._snap_available_model)
        self._region.snap_channel_list = self._get_list_from_model(self._snap_used_model)
        self._update_dialogs()

    def _video_available_list_move(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._list_move(self.regions_dialog.video_available_list_view,
                        self._video_available_model,
                        self._video_used_model)
        self._region.video_channel_list = self._get_list_from_model(self._video_used_model)
        self._update_dialogs()

    def _video_used_list_move(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._list_move(self.regions_dialog.video_used_list_view,
                        self._video_used_model,
                        self._video_available_model)
        self._region.video_channel_list = self._get_list_from_model(self._video_used_model)
        self._update_dialogs()

    def _start_x_line_edit_event(self, text):
        # Sets x_pos in region
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            self._htls_settings.start_pos[0] = int(text)
            self._update_dialogs()

    def _start_y_line_edit_event(self, text):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            self._htls_settings.start_pos[1] = int(text)
            self._update_dialogs()

    def _start_z_line_edit_event(self, text):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            self._htls_settings.start_pos[2] = int(text)
            self._update_dialogs()

    def num_fish_line_edit_event(self, text):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            self._htls_settings.num_fish = int(text)
            self._update_dialogs()

    def _fish_type_line_edit_event(self, text):
        # Changes fish type text for current fish
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._fish.fish_type = text
        self._acq_settings.write_to_config()

    def _age_line_edit_event(self, text):
        # Changes fish age text for current fish
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._fish.age = text
        self._acq_settings.write_to_config()

    def _treatment_line_edit_event(self, text):
        # Changes inoculum type text for current fish
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._fish.treatment = text
        self._acq_settings.write_to_config()

    def _add_notes_text_edit_event(self):
        # For now, removed logging from this event. Currently is triggered off of textChanged
        # which triggers every single time the text is set (via user or the program) which
        # floods the logs. Couldn't find a different signal for QT Text Edit.
        text = self.regions_dialog.add_notes_text_edit.toPlainText()
        self._fish.add_notes = text
        self._acq_settings.write_to_config()

    def _step_size_line_edit_event(self, text):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            # without this extra validation, user input could be 0, which would
            # break the acquisition script.
            if self.regions_dialog.step_size_line_edit.hasAcceptableInput():
                self._region.z_stack_step_size = int(text)
            self._update_dialogs()

    def _snap_exposure_line_edit_event(self, text):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            if self.regions_dialog.snap_exposure_line_edit.hasAcceptableInput():
                self._region.snap_exposure = float(text)
                self._update_region_table()
            else:
                self._update_dialogs()

    def _video_num_frames_line_edit_event(self, text):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            if self.regions_dialog.video_num_frames_line_edit.hasAcceptableInput():
                self._region.video_num_frames = int(text)
            self._update_dialogs()

    def _video_exposure_line_edit_event(self, text):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            if self.regions_dialog.video_exposure_line_edit.hasAcceptableInput():
                self._region.video_exposure = float(text)
                self._update_region_table()
            else:
                self._update_dialogs()

    def _channel_move_up_button_clicked(self):
        # Moves channel one index lower in channel_order_list.

        # There's gotta be a more elegant way to achieve this. I tried swapping elements in the channel_order_list
        # and then updating the list_view from the list, but there doesn't seem to be a way to maintain focus of
        # the same item after moving unless you do this implementation.
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(IndexError):
            channel_index = self._acq_settings_dialog.channel_order_list_view.selectedIndexes()[0].row()
            if channel_index > 0:
                channel = self._channel_order_model.takeRow(channel_index)
                self._channel_order_model.insertRow(channel_index - 1, channel)
                new_index = self._channel_order_model.indexFromItem(channel[0])
                self._acq_settings_dialog.channel_order_list_view.setCurrentIndex(new_index)

            # updating acq_dialog makes the list lose focus, which makes these buttons to not work
            # correctly, so this function just writes to config and updates the order list.
            self._acq_settings.channel_order_list = self._get_list_from_model(self._acq_order_model)
            self._update_regions_dialog()
            self._acq_settings.write_to_config()

    def _channel_move_down_button_clicked(self):
        # Same as move_up but moves channel down
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(IndexError):
            channel_index = self._acq_settings_dialog.channel_order_list_view.selectedIndexes()[0].row()
            if channel_index < self._channel_order_model.rowCount() - 1:
                channel = self._channel_order_model.takeRow(channel_index)
                self._channel_order_model.insertRow(channel_index + 1, channel)
                new_index = self._channel_order_model.indexFromItem(channel[0])
                self._acq_settings_dialog.channel_order_list_view.setCurrentIndex(new_index)
            self._acq_settings.channel_order_list = self._get_list_from_model(self._acq_order_model)
            self._update_regions_dialog()
            self._acq_settings.write_to_config()

    def _adv_settings_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._adv_settings_dialog.show()
        self._adv_settings_dialog.activateWindow()

    def _browse_button_clicked(self):
        # Opens up file browser to choose save directory.
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        browse = BrowseDialog()
        start_path = str(Path(self._acq_settings.directory).parent)
        path = str(browse.getExistingDirectory(browse, "Select Directory", start_path))
        if path:
            self._acq_settings.directory = path
            self._acq_settings_dialog.save_path_line_edit.setText(path)

    def _save_path_line_edit_event(self, text):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        # TODO feels wrong to not have any validation for this. Will probably make a dir validation
        # string at some point in globals
        self._acq_settings.directory = text

    def _researcher_line_edit_event(self, text):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._acq_settings.researcher = text

    def _start_acquisition_button_clicked(self):
        # Starts acquisition with current acq_settings instance.
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        # Update before starting acquisition to update all values beforehand.
        self._update_dialogs()
        try:
            if self._acquisition.is_alive():
                return
        except AttributeError:
            pass
        finally:
            abort_flag = exceptions.AbortFlag()
            self._acquisition = HTLSAcquisition(self._htls_settings, 
                                                HTLSAcqGui(self._acq_dialog, AbortDialog(), abort_flag), 
                                                AcqDirectory(self._acq_settings.directory), 
                                                abort_flag)
        self._acq_dialog.show()
        self._acq_dialog.activateWindow()
        self._acquisition.start()

    def _show_acquisition_dialog_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._acq_dialog.show()
        self._acq_dialog.activateWindow()

    def _z_stack_spectral_check_clicked(self, checked):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._adv_settings.spectral_z_stack_enabled = checked
        self._update_dialogs()

    def _stage_speed_combo_box_clicked(self):
        # The maximum exposure time during a scan
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._adv_settings.z_stack_stage_speed = float(self._adv_settings_dialog.stage_speed_combo_box.currentText())
        self._update_dialogs()

    def _custom_exposure_check_box_clicked(self, checked):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._adv_settings_dialog.z_stack_exposure_line_edit.setEnabled(checked)
        if Camera is Hamamatsu:
            self._adv_settings.edge_trigger_enabled = checked
        self._update_dialogs()

    def _z_stack_exposure_line_edit_event(self, text):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            if self._adv_settings_dialog.z_stack_exposure_line_edit.hasAcceptableInput():
                exp = float(text)
                self._adv_settings.z_stack_exposure = exp
                #If exp is outside of the acceptable range in the z_stack_exposure setter, z_stack_exposure will be 
                #different from exp. In this case, update the GUI to the actual value of z_stack_exposure.
                if self._adv_settings.z_stack_exposure != exp:
                    self._update_dialogs()
            else:
                self._update_dialogs()

    def _lsrm_check_box_clicked(self, checked):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._adv_settings.lsrm_enabled = checked
        self._update_dialogs()

    def _video_spectral_check_clicked(self, checked):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._adv_settings.spectral_video_enabled = checked
        self._update_dialogs()

    def _backup_directory_check_clicked(self):
        # Choose save location. Acquisition button is only enabled after setting save location.
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._adv_settings.backup_directory_enabled = self._adv_settings_dialog.backup_directory_check_box.isChecked()
        self._update_dialogs()

    def _second_browse_button_clicked(self):
        # Choose save location. Acquisition button is only enabled after setting save location.
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        browse = BrowseDialog()
        start_path = str(Path(self._adv_settings.backup_directory).parent)
        path = str(browse.getExistingDirectory(browse, "Select Directory", start_path))
        if path:
            self._adv_settings.backup_directory = path
            self._adv_settings_dialog.backup_directory_line_edit.setText(path)
        self._update_dialogs()

    def _backup_directory_line_edit_event(self, text):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._adv_settings.backup_directory = text
        self._update_dialogs()

    def _end_videos_check_box_clicked(self, checked):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._adv_settings.end_videos_enabled = checked
        self._update_dialogs()

    def _end_videos_num_frames_line_edit_event(self, text):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            if self._adv_settings_dialog.end_videos_num_frames_line_edit.hasAcceptableInput():
                self._adv_settings.end_videos_num_frames = int(text)
            self._update_dialogs()

    def _end_videos_exposure_line_edit(self, text):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            if self._adv_settings_dialog.end_videos_exposure_line_edit.hasAcceptableInput():
                self._adv_settings.end_videos_exposure = float(text)
                self._update_region_table()
            else:
                self._update_dialogs()
