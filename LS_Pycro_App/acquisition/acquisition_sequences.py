import time
import numpy as np
import logging
from abc import ABC, abstractmethod
from copy import deepcopy
from hardware import stage
from utils import constants, dir_functions, exceptions
from views.shared import AcqDialog
from models.acquisition.acq_settings import AcqSettings, Fish, Region
from models.acquisition.acq_directory import AcqDirectory
from acquisition import imaging_sequences

class AcquisitionSequence(ABC):
    # Reason for this is that disks write slower when they're full, which will cause timing
    # issues between timepoints.
    PERCENT_DISK_LIMIT = 0.8
    # If image sequence fails, reattempts this many times.
    ATTEMPT_LIMIT = 2
    # delay is pretty arbitrary. At the very least should be less than a second
    # to avoid inconsistent intervals between timepoints.
    TIME_UPDATE_DELAY_S = .01

    @abstractmethod
    def run_acquisition(self):
        """
        starts acquisition.
        """
        pass

    def __init__(self, acq_settings: AcqSettings, acq_dialog: AcqDialog,
                 abort_flag: exceptions.AbortFlag, acq_directory: AcqDirectory):
        self._logger = logging.getLogger(self._get_name())
        #deepcopy so that if GUI is changed during acquisition is in progress, won't change running acquisition
        self._acq_settings = deepcopy(acq_settings)
        self._adv_settings = self._acq_settings.adv_settings
        self._acq_dialog = acq_dialog
        self._abort_flag = abort_flag
        self._acq_directory = acq_directory

    def _get_name(self):
        return self.__class__.__name__

    # time point helpers
    def _begin_new_time_point(self, time_point: int):
        """
        updates time point label in acq_dialog and returns start time.
        """
        self._abort_check()
        self._time_point_num_update(time_point)
        return self._get_time()
    
    def _is_time_point_left(self, time_point):
        if self._acq_settings.time_points_enabled:
            time_points_left = self._acq_settings.num_time_points - time_point
            is_time_point_left = time_points_left > 1
        else:
            is_time_point_left = False
        return is_time_point_left

    def _wait_for_next_time_point(self, start_time):
        while self._time_remaining(start_time) > 0:
            self._abort_check()
            self._time_left_dialog_update(start_time)
            time.sleep(self.TIME_UPDATE_DELAY_S)

    def _get_time(self):
        return time.time()

    def _time_remaining(self, start_time):
        return self._acq_settings.time_points_interval_sec - self._time_since_start(start_time)

    def _time_since_start(self, start_time):
        return self._get_time() - start_time

    def _acquire_fish_regions(self, fish: Fish):
        for region_num, region in enumerate(fish.region_list):
            self._abort_check()
            if region.is_imaging_enabled():
                self._region_num_update(region_num)

                self._move_to_region(region)
                self._run_imaging_sequences(region)

    def _run_imaging_sequences(self, region: Region):
        self._abort_check()
        if region.snap_enabled:
            self._status_update("Initializing Snap")
            self._acquire_snap(region)

        self._abort_check()
        if region.video_enabled:
            self._status_update("Initializing Video")
            if self._adv_settings.spectral_video_enabled:
                self._acquire_spectral_video(region)
            else:
                self._acquire_video(region)

        self._abort_check()
        if region.z_stack_enabled:
            self._status_update("Initializing Z Stack")
            if self._adv_settings.spectral_z_stack_enabled:
                self._acquire_spectral_z_stack(region)
            else:
                self._acquire_z_stack(region)

    def _acquire_snap(self, region: Region):
        # This update message pattern works with the use of the "yield" keyword. See acquisition_scripts
        # for more details.
        snap = imaging_sequences.Snap(region, self._acq_settings, self._abort_flag, self._acq_directory)
        for update_message in snap.run():
            self._status_update(update_message)

    def _acquire_video(self, region: Region):
        for attempt_num in range(self.ATTEMPT_LIMIT):
            try:
                video = imaging_sequences.Video(region, self._acq_settings, self._abort_flag, self._acq_directory)
                for update_message in video.run():
                    self._status_update(update_message)
            except exceptions.CameraTimeoutException:
                self._camera_timeout_dialog_update(attempt_num, "Video")
            else:
                break

    def _acquire_spectral_video(self, region: Region):
        spectral_video = imaging_sequences.SpectralVideo(region, self._acq_settings, self._abort_flag, self._acq_directory)
        for update_message in spectral_video.run():
            self._status_update(update_message)

    def _acquire_z_stack(self, region: Region):
        for attempt_num in range(self.ATTEMPT_LIMIT):
            try:
                z_stack = imaging_sequences.ZStack(region, self._acq_settings, self._abort_flag, self._acq_directory)
                for update_message in z_stack.run():
                    self._status_update(update_message)
            except exceptions.CameraTimeoutException:
                self._camera_timeout_dialog_update(attempt_num, "Z Stack")
            else:
                break

    def _acquire_spectral_z_stack(self, region: Region):
        spectral_z_stack = imaging_sequences.SpectralZStack(region, self._acq_settings, self._abort_flag, self._acq_directory)
        for update_message in spectral_z_stack.run():
            self._status_update(update_message)

    def _move_to_region(self, region: Region):
        self._abort_check()
        self._status_update("Moving to region")
        if region.z_stack_enabled and not (region.snap_enabled or region.video_enabled):
            stage.move_stage(region.x_pos, region.y_pos, region.z_stack_start_pos)
        else:
            stage.move_stage(region.x_pos, region.y_pos, region.z_pos)

    def _get_start_region(self, start_fish_num):
        for fish in self._acq_settings.fish_list[start_fish_num:]:
            if fish.is_imaging_enabled():
                for region in fish.region_list:
                    if region.is_imaging_enabled():
                        return region, self._acq_settings.fish_list.index(fish)
        else:
            return None, None

    # directory methods
    def _update_directory(self, fish: Fish):
        if not (self._second_path_in_root() or self._is_enough_space(fish)):
            self._acq_directory.change_root(self._adv_settings.backup_directory)

    def _second_path_in_root(self):
        return self._adv_settings.backup_directory in self._acq_directory.root

    def _is_enough_space(self, fish: Fish):
        return dir_functions.is_enough_space(self._get_size_mb_of_fish(fish), self.PERCENT_DISK_LIMIT, self._acq_directory.root)

    def _get_size_mb_of_fish(self, fish: Fish):
        return fish.num_images*self._acq_settings.image_size_mb

    # acq_dialog methods
    def _set_region_label_num(self, region_num):
        self._acq_dialog.region_label.setText(f"Region {region_num + 1}")

    def _set_fish_label_num(self, fish_num: int):
        self._acq_dialog.fish_label.setText(f"Fish {fish_num + 1}")

    def _set_time_point_label_num(self, time_point: int):
        self._acq_dialog.time_point_label.setText(f"Time Point {time_point + 1}")

    def _camera_timeout_dialog_update(self, attempt_num: int, acq_type: str):
        message = f"{acq_type} failed. "
        if attempt_num < self.ATTEMPT_LIMIT - 1:
            message += f"reattempting {acq_type}."
        else:
            message += "skipping."

        self._status_update(message)

    def _time_left_dialog_update(self, start_time):
        minutes_left, remaining_seconds = self._get_minutes_and_seconds_left(start_time)

        update_message = "next time point:"
        if minutes_left:
            update_message = f"{update_message} {minutes_left} minutes"
        update_message = f"{update_message} {remaining_seconds} seconds"

        self._acq_dialog.acq_label.setText(update_message)

    def _get_minutes_and_seconds_left(self, start_time):
        total_seconds_left = int(np.ceil(self._time_remaining(start_time)))
        return divmod(total_seconds_left, constants.S_IN_MIN)

    def _status_update(self, message):
        """
        Displays message on acquisition label and writes it to logs
        """
        self._acq_dialog.acq_label.setText(message)
        self._logger.info(message)

    #general helpers
    def _region_num_update(self, region_num):
        self._acq_directory.set_region_num(region_num)
        self._set_region_label_num(region_num)
        self._status_update(f"Acquiring region {region_num + 1}")
    
    def _fish_num_update(self, fish_num):
        self._acq_directory.set_fish_num(fish_num)
        self._set_fish_label_num(fish_num)
        self._status_update(f"Acquiring fish {fish_num + 1}")

    def _time_point_num_update(self, time_point_num):
        self._acq_directory.set_time_point(time_point_num)
        self._set_time_point_label_num(time_point_num)
        self._status_update(f"Acquiring timepoint {time_point_num + 1}")

    def _abort_check(self):
        if self._abort_flag.abort:
            raise exceptions.AbortAcquisitionException

class TimeSampAcquisition(AcquisitionSequence):
    def run_acquisition(self):
        start_region = self._get_start_region(0)[0]
        if not start_region:
            raise exceptions.AbortAcquisitionException("No region in list with imaging enabled")
        self._acquire_time_points(start_region)

    def _acquire_time_points(self, start_region):
        self._move_to_region(start_region)
        for time_point in range(self._acq_settings.num_time_points):
            start_time = self._begin_new_time_point(time_point)

            self._acquire_fish()
            if self._is_time_point_left(time_point):
                self._move_to_region(start_region)
                self._wait_for_next_time_point(start_time)
            else:
                break

        self._move_to_region(start_region)

    def _acquire_fish(self):
        for fish_num, fish in enumerate(self._acq_settings.fish_list):
            self._abort_check()
            if fish.is_imaging_enabled():
                self._update_directory(fish)
                self._fish_num_update(fish_num)

                self._acquire_fish_regions(fish)


class SampTimeAcquisition(AcquisitionSequence):
    def run_acquisition(self):
        if not self._get_start_region()[0]:
            raise exceptions.AbortAcquisitionException("No valid region for imaging")
        self._acquire_fish()

    def _acquire_fish(self):
        fish_num = 0
        while True:
            self._abort_check()
            start_region, fish_num = self._get_start_region(fish_num)
            if not start_region or not fish_num:
                break
            fish = self._acq_settings.fish_list[fish_num]

            self._update_directory(fish)
            self._fish_num_update(fish_num)

            self._move_to_region(start_region)
            self._acquire_time_points(fish, start_region)
            fish_num += 1

    def _acquire_time_points(self, fish: Fish, start_region: Region):
        for time_point in range(self._acq_settings.num_time_points):
            start_time = self._begin_new_time_point(time_point)
            self._acquire_fish_regions(fish)

            if self._is_time_point_left(time_point):
                self._move_to_region(start_region)
                self._wait_for_next_time_point(start_time)
            else:
                break


class PositionTimeAcquisition(AcquisitionSequence):
    def run_acquisition(self):
        if not self._get_start_region(0)[0]:
            raise exceptions.AbortAcquisitionException("No valid region for imaging")
        self._acquire_regions()

    def _acquire_time_points(self, region: Region):
        for time_point in range(self._acq_settings.num_time_points):
            start_time = self._begin_new_time_point(time_point)

            self._run_imaging_sequences(region)
            if self._is_time_point_left(time_point):
                self._wait_for_next_time_point(start_time)
            else:
                break

    def _acquire_regions(self):
        for fish_num, fish in enumerate(self._acq_settings.fish_list):
            self._fish_num_update(fish_num)
            for region_num, region in enumerate(fish.region_list):
                self._abort_check()
                if region.is_imaging_enabled():
                    self._region_num_update(region_num)

                    self._move_to_region(region)
                    self._acquire_time_points(region)
