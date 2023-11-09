import sys
import logging
import contextlib
from copy import deepcopy
from pathlib import Path
from PyQt5 import QtGui, QtWidgets
from LS_Pycro_App.acquisition.sequences.main import Acquisition
from LS_Pycro_App.acquisition.models.acq_settings import Region, Fish, AcqSettings
from LS_Pycro_App.acquisition.models.adv_settings import AcqOrder
from LS_Pycro_App.acquisition.views.py import AcqRegionsDialog, AcqOrderDialog, AcqSettingsDialog, AdvSettingsDialog, BrowseDialog
from LS_Pycro_App.hardware import Stage, Camera
from LS_Pycro_App.utils import constants, exceptions
from LS_Pycro_App.utils.pycro import core


class AcqController(object):
    """
    This is the controller of the MVC framework formed by AcqSettings, 
    AcquisitionRegionsDialog (and AcquisitionDialog), and this class. This class controls
    the gui value display and logic, and controls an instance of AcqSettings
    to hold data from user input. 

    In addition, it starts the image acquisition through the Thread inherited start() method
    in the Acquisition class.

    ## Design Notes

    This class uses a pseudo-pointer system to keep track of and update the correct instances of Fish
    and Region. self._fish and self._region are assigned to elements in self._acq_settings.fish_list 
    and fish.region_list through the use of fish_num and region_num indexes. Since lists are mutable,
    changing self._fish after assigning it to an element in acq_settings.fish_list will change
    the element itself (it's a reference to the same object in memory).

    If an element doesn't exist at the index specified by fish_num or region_num, a new instance is
    created at self._fish or self._region, but is not immediately initialized to fish_list or region_list. 
    New elements are only initialized in their respective list when either the set region or paste region 
    button is pressed by the user. This is to prevent unwanted/empty regions from being initialized.

    ## Future Changes:

    - This is by far the most boilerplatey/gross file in the whole application. Main way to fix this 
    is to find a better way to connect PyQt5 buttons to methods.

    - I go back and forth on whether the GUI button states should be set in their
    individual action listener events or if there should be a single function that 
    is called that updates all GUI elements at once. Currently, it's the latter.
    From a readability perspective, I like it this way. If performance ever becomes an
    issue (I doubt it ever will), it should switch to the prior.

    - Color code table so that regions from the same fish are the same color

    - Not sure how to deal with new instances of region. When a new instance of
    region is created, how should the GUI change? Should it be blank?
    Should it show the default values? For now, uses class attributes in data
    classes as default values and updates them to most recently set values.

    - User entry validation could be much better. Perhaps creating entry formats would be useful,
    especially for things like directories.

    - _set_table() is awful. There's probably a better way to do this. God I hate coding GUI.

    - For now, acq_settings (the model) and the dialogs (view) are initialized inside the controller class.
    Should be fine for now, but if any of these were to be extended, they should probably be added as arguments
    in the constructor (__init__()).
    """
    
    NUM_DECIMAL_PLACES = 3

    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)
        self.regions_dialog = AcqRegionsDialog()
        self._acq_settings_dialog = AcqSettingsDialog()
        self._adv_settings_dialog = AdvSettingsDialog()
        self._acq_order_dialog = AcqOrderDialog()
        self._acq_settings = AcqSettings()
        self._adv_settings = self._acq_settings.adv_settings
        self._acquisition = Acquisition(self._acq_settings)

        self._fish_num = 0
        self._region_num = 0
        self._fish = Fish()
        self._region = Region()
        self._fish_copy = deepcopy(self._fish)
        self._region_copy = deepcopy(self._region)

        self._set_widget_models()
        self._set_validators()
        self._connect_signals()
        self._set_additional_widget_settings()
        self._refresh_dialogs()
    
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
        self._adv_settings_dialog.acq_order_combo_box.setModel(self._acq_order_model)

        # uses core channel list to initialize list model values
        for channel in self._acq_settings.core_channel_list:
            self._z_stack_available_model.appendRow(QtGui.QStandardItem(channel))
            self._snap_available_model.appendRow(QtGui.QStandardItem(channel))
            self._video_available_model.appendRow(QtGui.QStandardItem(channel))

        for speed in self._adv_settings.speed_list:
            item = QtGui.QStandardItem(str(speed))
            self._speed_list_model.appendRow(item)
        self._adv_settings_dialog.stage_speed_combo_box.setCurrentText(str(self._adv_settings.z_stack_stage_speed))

        for order in AcqOrder:
            item = QtGui.QStandardItem(order.name)
            self._acq_order_model.appendRow(item)

    def _set_validators(self):
        # Validators and extra properties
        validator = QtGui.QIntValidator()
        self.regions_dialog.x_line_edit.setValidator(validator)
        self.regions_dialog.y_line_edit.setValidator(validator)
        self.regions_dialog.z_line_edit.setValidator(validator)
        self.regions_dialog.start_z_line_edit.setValidator(validator)
        self.regions_dialog.end_z_line_edit.setValidator(validator)

        validator = QtGui.QIntValidator()
        validator.setBottom(0)
        self._acq_settings_dialog.time_points_interval_line_edit.setValidator(validator)

        validator = QtGui.QIntValidator()
        validator.setBottom(1)
        self.regions_dialog.step_size_line_edit.setValidator(validator)
        self.regions_dialog.video_num_frames_line_edit.setValidator(validator)
        self._acq_settings_dialog.num_time_points_line_edit.setValidator(validator)

        validator = QtGui.QDoubleValidator()
        validator.setDecimals(AcqController.NUM_DECIMAL_PLACES)
        validator.setBottom(Camera.MIN_EXPOSURE)
        validator.setTop(Camera.MAX_EXPOSURE)
        self.regions_dialog.snap_exposure_line_edit.setValidator(validator)
        self.regions_dialog.video_exposure_line_edit.setValidator(validator)
        self._adv_settings_dialog.z_stack_exposure_line_edit.setValidator(validator)
    
    def _connect_signals(self):
        # Initialize AcquisitionRegionsDialog event handlers. Organized by where they show up in the GUI.
        # TODO find a less ugly/more automated way of doing this. Yikes.
        self.regions_dialog.go_to_button.clicked.connect(self._go_to_button_clicked)
        self.regions_dialog.set_region_button.clicked.connect(self._set_region_button_clicked)
        self.regions_dialog.x_line_edit.textEdited.connect(self._x_line_edit_event)
        self.regions_dialog.y_line_edit.textEdited.connect(self._y_line_edit_event)
        self.regions_dialog.z_line_edit.textEdited.connect(self._z_line_edit_event)

        self.regions_dialog.fish_type_line_edit.textEdited.connect(self._fish_type_line_edit_event)
        self.regions_dialog.age_line_edit.textEdited.connect(self._age_line_edit_event)
        self.regions_dialog.inoculum_line_edit.textEdited.connect(self._inoculum_line_edit_event)
        self.regions_dialog.add_notes_text_edit.textChanged.connect(self._add_notes_text_edit_event)

        self.regions_dialog.copy_region_button.clicked.connect(self._copy_button_clicked)
        self.regions_dialog.paste_region_button.clicked.connect(self._paste_button_clicked)
        self.regions_dialog.prev_fish_button.clicked.connect(self._prev_fish_button_clicked)
        self.regions_dialog.prev_region_button.clicked.connect(self._prev_region_button_clicked)
        self.regions_dialog.remove_region_button.clicked.connect(self._remove_region_button_clicked)
        self.regions_dialog.next_region_button.clicked.connect(self._next_region_button_clicked)
        self.regions_dialog.next_fish_button.clicked.connect(self._next_fish_button_clicked)

        self.regions_dialog.z_stack_check_box.clicked.connect(self._z_stack_check_clicked)
        self.regions_dialog.set_z_start_button.clicked.connect(self._set_z_start_button_clicked)
        self.regions_dialog.start_z_line_edit.textEdited.connect(self._start_z_line_edit_event)
        self.regions_dialog.set_z_end_button.clicked.connect(self._set_z_end_button_clicked)
        self.regions_dialog.end_z_line_edit.textEdited.connect(self._end_z_line_edit_event)
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
        self._acq_settings_dialog.time_points_check_box.clicked.connect(self._time_points_check_clicked)
        self._acq_settings_dialog.num_time_points_line_edit.textEdited.connect(self._num_time_points_line_edit_event)
        self._acq_settings_dialog.time_points_interval_line_edit.textEdited.connect(
            self._time_points_interval_line_edit_event)

        self._acq_settings_dialog.channel_order_move_up_button.clicked.connect(self._channel_move_up_button_clicked)
        self._acq_settings_dialog.channel_order_move_down_button.clicked.connect(self._channel_move_down_button_clicked)

        self._acq_settings_dialog.adv_settings_button.clicked.connect(self._adv_settings_button_clicked)

        self._acq_settings_dialog.browse_button.clicked.connect(self._browse_button_clicked)
        self._acq_settings_dialog.save_path_line_edit.textEdited.connect(self._save_path_line_edit_event)
        self._acq_settings_dialog.researcher_line_edit.textEdited.connect(self._researcher_line_edit_event)
        self._acq_settings_dialog.start_acquisition_button.clicked.connect(self._start_acquisition_button_clicked)
        self._acq_settings_dialog.show_acquisition_dialog_button.clicked.connect(
            self._show_acquisition_dialog_button_clicked)

        # Initialize AdvancedSettingsDialog event handlers
        self._adv_settings_dialog.z_stack_spectral_check_box.clicked.connect(self._z_stack_spectral_check_clicked)
        self._adv_settings_dialog.stage_speed_combo_box.activated.connect(self._stage_speed_combo_box_clicked)
        self._adv_settings_dialog.z_stack_exposure_line_edit.textEdited.connect(self._z_stack_exposure_line_edit_event)

        self._adv_settings_dialog.video_spectral_check_box.clicked.connect(self._video_spectral_check_clicked)

        self._adv_settings_dialog.acq_order_combo_box.activated.connect(self._acq_order_combo_box_clicked)
        self._acq_order_dialog.yes_button.clicked.connect(self._acq_order_yes_button_clicked)
        self._acq_order_dialog.cancel_button.clicked.connect(self._acquisition_order_cancel_button_clicked)

        self._adv_settings_dialog.backup_directory_check_box.clicked.connect(self._backup_directory_check_clicked)
        self._adv_settings_dialog.backup_directory_browse_button.clicked.connect(self._second_browse_button_clicked)
        self._adv_settings_dialog.backup_directory_line_edit.textEdited.connect(self._backup_directory_line_edit_event)

    def _set_additional_widget_settings(self):
        self._acq_settings_dialog.channel_order_list_view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.regions_dialog.region_table_view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        # Want these to be uneditable since they're set by the application
        self._acq_settings_dialog.num_images_per_line_edit.setEnabled(False)
        self._acq_settings_dialog.total_images_line_edit.setEnabled(False)
        self._acq_settings_dialog.memory_line_edit.setEnabled(False)

    def _refresh_dialogs(self):
        """
        Refreshes all dialogs to match model. 

        Most of the time, all of these are called together. However, there are cases where certain
        GUI elements updating can mess with GUI interactions, and so in those cases, only a selection
        of these functions are called.
        """
        #acq_settings.update() doesn't quite fit in with other refresh methods, since this is actually an update 
        #of the model based on settings in model and core, but this should be called frequently anyway and it seems
        #like a decent spot or it.
        if not self._acquisition.is_alive():
            self._acq_settings.update()
        self._reresh_regions_dialog()
        self._refresh_region_table()
        self._refresh_acq_settings_dialog()
        self._refresh_adv_settings_dialog()
        self._acq_settings.write_to_config()

    def _refresh_acq_settings_dialog(self):
        """
        Updates all GUI elements (in PyQt5, widgets) of acq_settings_dialog to reflect the 
        current values in acq_settings
        """
        self._refresh_timepoints_widgets()
        self._refresh_channel_order_model()
        self._refresh_save_path_widgets()
        self._refresh_memory_widgets()

    # _update_acq_settings_dialog helpers
    def _refresh_timepoints_widgets(self):
        self._acq_settings_dialog.time_points_check_box.setChecked(self._acq_settings.time_points_enabled)
        self._acq_settings_dialog.num_time_points_line_edit.setEnabled(self._acq_settings.time_points_enabled)
        self._acq_settings_dialog.num_time_points_line_edit.setText(str(self._acq_settings.num_time_points))
        self._acq_settings_dialog.time_points_interval_line_edit.setEnabled(self._acq_settings.time_points_enabled)
        self._acq_settings_dialog.time_points_interval_line_edit.setText(
            str(self._acq_settings.time_points_interval_sec))

    def _refresh_channel_order_model(self):
        self._channel_order_model.clear()
        for channel in self._acq_settings.channel_order_list:
            self._channel_order_model.appendRow(QtGui.QStandardItem(channel))

    def _refresh_save_path_widgets(self):
        self._acq_settings_dialog.save_path_line_edit.setText(self._acq_settings.directory)
        self._acq_settings_dialog.researcher_line_edit.setText(self._acq_settings.researcher)

    def _refresh_memory_widgets(self):
        if self._adv_settings.acq_order == AcqOrder.TIME_SAMP:
            self._acq_settings_dialog.num_images_per_line_edit.setText(str(self._acq_settings.images_per_time_point))
            self._acq_settings_dialog.total_images_line_edit.setText(str(self._acq_settings.total_num_images))
        elif self._adv_settings.acq_order == AcqOrder.SAMP_TIME:
            # NA because different fish have different number of images
            self._acq_settings_dialog.num_images_per_line_edit.setText("N/A")
            self._acq_settings_dialog.total_images_line_edit.setText(str(self._acq_settings.total_num_images))
        elif self._adv_settings.acq_order == AcqOrder.POS_TIME:
            # NA because different regions have different numbers of images
            self._acq_settings_dialog.num_images_per_line_edit.setText("N/A")
            self._acq_settings_dialog.total_images_line_edit.setText(str(self._acq_settings.total_num_images))

        memory_gb = self._acq_settings.total_num_images*AcqSettings.image_size_mb*constants.MB_TO_GB
        self._acq_settings_dialog.memory_line_edit.setText(str(round(memory_gb, AcqController.NUM_DECIMAL_PLACES)))

    def _refresh_adv_settings_dialog(self):
        self._refresh_adv_z_stack_widgets()
        self._refresh_adv_video_widgets()
        self.refresh_acq_order_widgets()
        self._refresh_adv_backup_directory_widgets()

    # update_adv_settings_dialog helpers
    def _refresh_adv_z_stack_widgets(self):
        self._adv_settings_dialog.z_stack_spectral_check_box.setChecked(self._adv_settings.spectral_z_stack_enabled)
        self._adv_settings_dialog.stage_speed_combo_box.setCurrentText(str(self._adv_settings.z_stack_stage_speed))
        self._adv_settings_dialog.z_stack_exposure_line_edit.setText(str(self._adv_settings.z_stack_exposure))

    def _refresh_adv_video_widgets(self):
        self._adv_settings_dialog.video_spectral_check_box.setChecked(self._adv_settings.spectral_video_enabled)

    def refresh_acq_order_widgets(self):
        self._adv_settings_dialog.acq_order_combo_box.setCurrentText(self._adv_settings.acq_order.name)

    def _refresh_adv_backup_directory_widgets(self):
        self._adv_settings_dialog.backup_directory_check_box.setChecked(self._adv_settings.backup_directory_enabled)
        self._adv_settings_dialog.backup_directory_browse_button.setEnabled(self._adv_settings.backup_directory_enabled)
        self._adv_settings_dialog.backup_directory_line_edit.setEnabled(self._adv_settings.backup_directory_enabled)
        self._adv_settings_dialog.backup_directory_line_edit.setText(self._adv_settings.backup_directory)

    def _reresh_regions_dialog(self):
        """
        Updates all GUI elements of AcquisitionRegionsDialog to reflect the values in the acq_settings
        fish list.

        First, self._fish and self._region pointers to elements specified by self._fish_num and self._region_num. 
        Then, updates all button states and line edits to match current intanes of fish and region.
        """
        fish_bool = self._update_fish()
        region_bool = self._update_region()
        self._region_widgets_update(region_bool)
        self._fish_widgets_state_update(fish_bool)
        self._fish_notes_update()
        self._position_labels_update()

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

    def _update_fish(self):
        fish_found = False
        try:
            self._fish = self._acq_settings.fish_list[self._fish_num]
            fish_found = True
        except IndexError:
            self._fish = Fish()

        return fish_found

    def _region_widgets_update(self, region_bool):
        """
        Updates region buttons 

        If region_bool == True, remove region, next region, and go to are enabled. Else, disabled.

        If self._region_num > 0, previous region button is enabled. Else, disabled.
        """
        self.regions_dialog.fish_label.setText(f"Fish {self._fish_num + 1}")
        self.regions_dialog.next_region_button.setEnabled(region_bool)
        self.regions_dialog.remove_region_button.setEnabled(region_bool)
        self.regions_dialog.go_to_button.setEnabled(region_bool)
        self.regions_dialog.prev_region_button.setEnabled(self._region_num > 0)

    def _fish_widgets_state_update(self, fish_bool):
        """
        Sets next fish button and previous fish button.

        If fish_bool == True, next fish button enabled. Else, disabled.

        If self._fish_num > 0, previous fish button is enabled. Else, disabled.
        """
        self.regions_dialog.region_label.setText(f"Region {self._region_num + 1}")
        self.regions_dialog.next_fish_button.setEnabled(fish_bool)
        self.regions_dialog.prev_fish_button.setEnabled(self._fish_num > 0)

    def _fish_notes_update(self):
        self.regions_dialog.fish_notes_label.setText(f"Fish {self._fish_num + 1} Notes")
        self.regions_dialog.fish_type_line_edit.setText(str(self._fish.fish_type))
        self.regions_dialog.age_line_edit.setText(str(self._fish.age))
        self.regions_dialog.inoculum_line_edit.setText(str(self._fish.inoculum))
        self.regions_dialog.add_notes_text_edit.setPlainText(str(self._fish.add_notes))

    def _position_labels_update(self):
        self.regions_dialog.x_line_edit.setText(str(self._region.x_pos))
        self.regions_dialog.y_line_edit.setText(str(self._region.y_pos))
        self.regions_dialog.z_line_edit.setText(str(self._region.z_pos))

    def _region_z_stack_widgets_update(self):
        """
        Updates all QtWidgets related to z_stack settings in regions_dialog.
        """
        z_stack_enabled = self._region.z_stack_enabled
        self.regions_dialog.z_stack_check_box.setChecked(z_stack_enabled)
        self.regions_dialog.set_z_start_button.setEnabled(z_stack_enabled)
        self.regions_dialog.start_z_line_edit.setEnabled(z_stack_enabled)
        self.regions_dialog.start_z_line_edit.setText(str(self._region.z_stack_start_pos))
        self.regions_dialog.set_z_end_button.setEnabled(z_stack_enabled)
        self.regions_dialog.end_z_line_edit.setEnabled(z_stack_enabled)
        self.regions_dialog.end_z_line_edit.setText(str(self._region.z_stack_end_pos))
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

    def _refresh_region_table(self):
        """
        Sets the table to display values in current region_list within
        acquistiion_settings.

        #TODO make this not as disgusting. Perhaps find a way to automatically set headers
        based on attributes names. Only problem is attribute names are long. Maybe just use 
        small font? Wrapping headers? idk but this is awful.
        """
        self._region_table_model.clear()
        headers = ["fish #", 
                   "reg #", 
                   "x", 
                   "y", 
                   "z", 
                   "z stack", 
                   "start",
                   "end", 
                   "step", 
                   "chans", 
                   "snap", 
                   "exp", 
                   "chans", 
                   "video",
                   "frames", 
                   "exp", 
                   "chans", 
                   "# images"]
        self._region_table_model.setHorizontalHeaderLabels(headers)
        for fish_num, fish in enumerate(self._acq_settings.fish_list):
            for region_num, region in enumerate(fish.region_list):
                row_list = [str(fish_num + 1), 
                            str(region_num + 1),
                            str(region.x_pos), 
                            str(region.y_pos),
                            str(region.z_pos), 
                            str(region.z_stack_enabled),
                            str(region.z_stack_start_pos), 
                            str(region.z_stack_end_pos),
                            str(region.z_stack_step_size), 
                            ','.join(region.z_stack_channel_list),
                            str(region.snap_enabled), 
                            str(region.snap_exposure),
                            ','.join(region.snap_channel_list), 
                            str(region.video_enabled),
                            str(region.video_num_frames), 
                            str(region.video_exposure),
                            ','.join(region.video_channel_list), 
                            str(region.num_images)]
                row_list = [QtGui.QStandardItem(element) for element in row_list]
                self._region_table_model.appendRow(row_list)
        self.regions_dialog.region_table_view.resizeColumnsToContents()

    def _go_to_button_clicked(self):
        # Goes to position set in current instance of Region
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        x_pos = self._region.x_pos
        y_pos = self._region.y_pos
        z_pos = self._region.z_pos
        if x_pos and y_pos and z_pos:
            with contextlib.suppress(exceptions.GeneralHardwareException):
                Stage.move_stage(x_pos, y_pos, z_pos)

        self._refresh_dialogs()

    def _set_region_button_clicked(self):
        # Gets current stage position and creates element of region_list
        # with current settings in GUI. Currently, this method and the paste_regionButton
        # are the only ways to initialize an element in the region_list.
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        x_pos, y_pos, z_pos = None, None, None
        with contextlib.suppress(exceptions.GeneralHardwareException):
            x_pos = Stage.get_x_position()
            y_pos = Stage.get_y_position()
            z_pos = Stage.get_z_position()

        if None not in (x_pos, y_pos, z_pos):
            # You'll notice this pattern of setting not only the instance attributes but also
            # the class attributes for Region. The class attributes are used as default values
            # for new class instances, so updating them updates the default values.
            self._region.x_pos = x_pos
            self._region.y_pos = y_pos
            self._region.z_pos = z_pos
            Region.x_pos = x_pos
            Region.y_pos = y_pos
            Region.z_pos = z_pos

            self._acq_settings.update_fish_list(self._fish_num, self._fish)
            self._fish.update_region_list(self._region_num, self._region)
        else:
            message = "Region cannot be set. Stage failed to return position."
            self._logger.info(message)
            print(message)

        self._refresh_dialogs()

    def _next_region_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._region_num += 1

        self._refresh_dialogs()

    def _prev_region_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._region_num -= 1

        self._refresh_dialogs()

    def _next_fish_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._fish_num += 1
        self._region_num = 0

        self._refresh_dialogs()

    def _prev_fish_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._fish_num -= 1
        self._region_num = 0

        self._refresh_dialogs()

    def _remove_region_button_clicked(self):
        # Removes current region from region_list.
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._fish.remove_region(self._region_num)

        if len(self._fish.region_list) == 0:
            self._acq_settings.remove_fish(self._fish_num)

        self._refresh_dialogs()

    def _copy_button_clicked(self):
        # Creates new object with fields of the same value as current region
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._region_copy = deepcopy(self._region)

    def _paste_button_clicked(self):
        # Initializes new region at current index with values from region_copy.
        # Currently the only method other than set_region_button_clicked to
        # initialize region in region_list.
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._region = deepcopy(self._region_copy)

        self._acq_settings.update_fish_list(self._fish_num, self._fish)
        self._fish.update_region_list(self._region_num, self._region)

        self._refresh_dialogs()

    def _set_z_start_button_clicked(self):
        # Gets current z stage position and sets it as z_start_position
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        z_pos = Stage.get_z_position()
        self._region.z_stack_start_pos = z_pos
        Region.z_stack_start_pos = z_pos

        self._refresh_dialogs()

    def _set_z_end_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        z_pos = Stage.get_z_position()
        self._region.z_stack_end_pos = z_pos
        Region.z_stack_end_pos = z_pos

        self._refresh_dialogs()

    def _acq_setup_button_clicked(self):
        # Brings up acquisition settings dialog
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._acq_settings_dialog.show()
        self._acq_settings_dialog.activateWindow()

    def _reset_joystick_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(exceptions.GeneralHardwareException):
            Stage.reset_joystick()

    def _z_stack_check_clicked(self):
        # Enables/disables z_stack GUI elements when checkbox is clicked.
        # Also sets z_stack_enabled in region.
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        z_stack_enabled = self.regions_dialog.z_stack_check_box.isChecked()
        self._region.z_stack_enabled = z_stack_enabled
        Region.z_stack_enabled = z_stack_enabled

        self._refresh_dialogs()

    def _snap_check_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        snap_enabled = self.regions_dialog.snap_check_box.isChecked()
        self._region.snap_enabled = snap_enabled
        Region.snap_enabled = snap_enabled

        self._refresh_dialogs()

    def _video_check_clicked(self):
        # Same as z_stack_check_clicked but for video
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        video_enabled = self.regions_dialog.video_check_box.isChecked()
        self._region.video_enabled = video_enabled
        Region.video_enabled = video_enabled

        self._refresh_dialogs()

    def _z_stack_available_list_move(self):
        # on double click, switches channel from available list to used list
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        channel_index = self.regions_dialog.z_stack_available_list_view.selectedIndexes()[0].row()
        channel = self._z_stack_available_model.item(channel_index).text()
        self._z_stack_available_model.removeRow(channel_index)
        self._z_stack_used_model.appendRow(QtGui.QStandardItem(channel))

        self._region.z_stack_channel_list.append(channel)
        Region.z_stack_channel_list = deepcopy(self._region.z_stack_channel_list)

        self._refresh_dialogs()

    def _z_stack_used_list_move(self):
        # Same as available_list_move except from used list to available list
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        channel_index = self.regions_dialog.z_stack_used_list_view.selectedIndexes()[0].row()
        channel = self._z_stack_used_model.item(channel_index).text()
        self.regions_dialog.z_stack_used_list_view.model().removeRow(channel_index)
        self._z_stack_available_model.appendRow(QtGui.QStandardItem(channel))

        self._region.z_stack_channel_list.remove(channel)
        Region.z_stack_channel_list = deepcopy(self._region.z_stack_channel_list)

        self._refresh_dialogs()

    def _snap_available_list_move(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        channel_index = self.regions_dialog.snap_available_list_view.selectedIndexes()[0].row()
        channel = self._snap_available_model.item(channel_index).text()
        self._snap_available_model.removeRow(channel_index)
        self._snap_used_model.appendRow(QtGui.QStandardItem(channel))

        self._region.snap_channel_list.append(channel)
        Region.snap_channel_list = deepcopy(self._region.snap_channel_list)

        self._refresh_dialogs()

    def _snap_used_list_move(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        channel_index = self.regions_dialog.snap_used_list_view.selectedIndexes()[0].row()
        channel = self._snap_used_model.item(channel_index).text()
        self._snap_used_model.removeRow(channel_index)
        self._snap_available_model.appendRow(QtGui.QStandardItem(channel))

        self._region.snap_channel_list.remove(channel)
        Region.snap_channel_list = deepcopy(self._region.snap_channel_list)

        self._refresh_dialogs()

    def _video_available_list_move(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        channel_index = self.regions_dialog.video_available_list_view.selectedIndexes()[0].row()
        channel = self._video_available_model.item(channel_index).text()
        self._video_available_model.removeRow(channel_index)
        self._video_used_model.appendRow(QtGui.QStandardItem(channel))

        self._region.video_channel_list.append(channel)
        Region.video_channel_list = deepcopy(self._region.video_channel_list)

        self._refresh_dialogs()

    def _video_used_list_move(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        channel_index = self.regions_dialog.video_used_list_view.selectedIndexes()[0].row()
        channel = self._video_used_model.item(channel_index).text()
        self._video_used_model.removeRow(channel_index)
        self._video_available_model.appendRow(QtGui.QStandardItem(channel))

        self._region.video_channel_list.remove(channel)
        Region.video_channel_list = deepcopy(self._region.video_channel_list)

        self._refresh_dialogs()

    def _x_line_edit_event(self, text):
        # Sets x_pos in region
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            x_pos = int(text)
            self._region.x_pos = x_pos
            Region.x_pos = x_pos

            self._refresh_dialogs()

    def _y_line_edit_event(self, text):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            y_pos = int(text)
            self._region.y_pos = y_pos
            Region.y_pos = y_pos

            self._refresh_dialogs()

    def _z_line_edit_event(self, text):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            z_pos = int(text)
            self._region.z_pos = z_pos
            Region.z_pos = z_pos

            self._refresh_dialogs()

    def _fish_type_line_edit_event(self, text):
        # Changes fish type text for current fish
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._fish.fish_type = text
        Fish.fish_type = text

    def _age_line_edit_event(self, text):
        # Changes fish age text for current fish
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._fish.age = text
        Fish.age = text

    def _inoculum_line_edit_event(self, text):
        # Changes inoculum type text for current fish
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._fish.inoculum = text
        Fish.inoculum = text

    def _add_notes_text_edit_event(self):
        # For now, removed logging from this event. Currently is triggered off of textChanged
        # which triggers every single time the text is set (via user or the program) which
        # floods the logs. Couldn't find a different signal for QT Text Edit.
        text = self.regions_dialog.add_notes_text_edit.toPlainText()
        self._fish.add_notes = text
        Fish.add_notes = text

    def _start_z_line_edit_event(self, text):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            z_pos = int(text)
            self._region.z_stack_start_pos = z_pos
            Region.z_stack_start_pos = z_pos

            self._refresh_dialogs()

    def _end_z_line_edit_event(self, text):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            z_pos = int(text)
            self._region.z_stack_end_pos = z_pos
            Region.z_stack_end_pos = z_pos

            self._refresh_dialogs()

    def _step_size_line_edit_event(self, text):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            step_size = int(text)
            # without this extra validation, user input could be 0, which would
            # break the acquisition script.
            if self.regions_dialog.step_size_line_edit.hasAcceptableInput():
                self._region.z_stack_step_size = step_size
                Region.z_stack_step_size = step_size

            self._refresh_dialogs()

    def _snap_exposure_line_edit_event(self, text):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            if self.regions_dialog.snap_exposure_line_edit.hasAcceptableInput():
                exp = float(text)
                self._region.snap_exposure = exp
                Region.snap_exposure = exp

                self._refresh_region_table()
            else:
                self._refresh_dialogs()

    def _video_num_frames_line_edit_event(self, text):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            num_frames = int(text)
            if self.regions_dialog.video_num_frames_line_edit.hasAcceptableInput():
                self._region.video_num_frames = num_frames
                Region.video_num_frames = num_frames

            self._refresh_dialogs()

    def _video_exposure_line_edit_event(self, text):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            if self.regions_dialog.video_exposure_line_edit.hasAcceptableInput():
                exp = float(text)
                self._region.video_exposure = exp
                Region.video_exposure = exp

                self._refresh_region_table()
            else:
                self._refresh_dialogs()

    def _time_points_check_clicked(self, checked):
        # Sets time_points_enabled to current state of checkbox
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._acq_settings.time_points_enabled = checked

        self._refresh_dialogs()

    def _num_time_points_line_edit_event(self, text):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            if self._acq_settings_dialog.num_time_points_line_edit.hasAcceptableInput():
                self._acq_settings.num_time_points = int(text)

            self._refresh_dialogs()

    def _time_points_interval_line_edit_event(self, text):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            if self._acq_settings_dialog.num_time_points_line_edit.hasAcceptableInput():
                self._acq_settings.time_points_interval_sec = int(text)

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
            self.update_channel_order_list()
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

            self.update_channel_order_list()
            self._acq_settings.write_to_config()

    # Helper for channel order buttons, since update_acq_settings_dialog can't be called.
    def update_channel_order_list(self):
        self._acq_settings.channel_order_list = []
        for index in range(self._channel_order_model.rowCount()):
            self._acq_settings.channel_order_list.append(self._channel_order_model.item(index, 0).text())

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
        self._refresh_dialogs()

        if not self._acquisition.is_alive():
            self._acquisition = Acquisition(self._acq_settings)

        self._acquisition._acq_dialog.show()
        self._acquisition._acq_dialog.activateWindow()
        self._acquisition.start()

    def _show_acquisition_dialog_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._acquisition._acq_dialog.show()
        self._acquisition._acq_dialog.activateWindow()

    def _z_stack_spectral_check_clicked(self, checked):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._adv_settings.spectral_z_stack_enabled = checked

        self._refresh_dialogs()

    def _stage_speed_combo_box_clicked(self):
        # The maximum exposure time during a scan
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._adv_settings.z_stack_stage_speed = float(self._adv_settings_dialog.stage_speed_combo_box.currentText())

        self._refresh_dialogs()

    def _z_stack_exposure_line_edit_event(self, text):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        with contextlib.suppress(ValueError):
            if self._adv_settings_dialog.z_stack_exposure_line_edit.hasAcceptableInput():
                exp = float(text)
                self._adv_settings.z_stack_exposure = exp
                #Only refresh dialog if exposure in adv_settings doesn't match gui, ie when
                #an exposure that is outside of the acceptable range is added.
                if self._adv_settings.z_stack_exposure != exp:
                    self._refresh_dialogs()
            else:
                self._refresh_dialogs()

    def _video_spectral_check_clicked(self, checked):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._adv_settings.spectral_video_enabled = checked

        self._refresh_dialogs()

    def _acq_order_combo_box_clicked(self):
        # Changes acquisition order. If SAMP_TIME is selected, prompts user to make sure
        # they want to change this setting.
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._acq_order_dialog.show()
        self._acq_order_dialog.activateWindow()

    def _acq_order_yes_button_clicked(self):
        # If confirmed, acquisition order is changed to SAMP_TIME
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._adv_settings.acq_order = AcqOrder[self._adv_settings_dialog.acq_order_combo_box.currentText()]
        self._acq_order_dialog.close()

        self._refresh_dialogs()

    def _acquisition_order_cancel_button_clicked(self):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._adv_settings_dialog.acq_order_combo_box.setCurrentText(self._adv_settings.acq_order.name)
        self._acq_order_dialog.close()

        self._refresh_dialogs()

    def _backup_directory_check_clicked(self):
        # Choose save location. Acquisition button is only enabled after setting save location.
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._adv_settings.backup_directory_enabled = self._adv_settings_dialog.backup_directory_check_box.isChecked()

        self._refresh_dialogs()

    def _second_browse_button_clicked(self):
        # Choose save location. Acquisition button is only enabled after setting save location.
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        browse = BrowseDialog()
        start_path = str(Path(self._adv_settings.backup_directory).parent)
        path = str(browse.getExistingDirectory(browse, "Select Directory", start_path))
        if path:
            self._adv_settings.backup_directory = path
            self._adv_settings_dialog.backup_directory_line_edit.setText(path)

        self._refresh_dialogs()

    def _backup_directory_line_edit_event(self, text):
        self._logger.info(sys._getframe().f_code.co_name.strip("_"))
        self._adv_settings.backup_directory = text

        self._refresh_dialogs()

