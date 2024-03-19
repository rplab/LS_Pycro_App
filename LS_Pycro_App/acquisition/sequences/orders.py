import time
import numpy as np
import logging
from abc import ABC, abstractmethod
from copy import deepcopy

from LS_Pycro_App.acquisition.views.py import AcqDialog
from LS_Pycro_App.acquisition.models.acq_settings import AcqSettings, Fish, Region
from LS_Pycro_App.acquisition.models.acq_directory import AcqDirectory
from LS_Pycro_App.acquisition.sequences.imaging import ImagingSequence, Snap, Video, SpectralVideo, ZStack, SpectralZStack
from LS_Pycro_App.hardware import Stage
from LS_Pycro_App.utils import constants, dir_functions, exceptions
from LS_Pycro_App.utils.pycro import BF_CHANNEL

class AcquisitionOrder(ABC):
    """
    Abstract class that controls the order of region, fish, and time points during image acquisition.
    Moves stage to region for imaging and then calls run() in imaging sequences to acquire images.
    Also sets region, fish, and time point in acq_directory so that save directory is initialized correctly. 
    Child classes should move to correct region and then call _run_imaging_sequences() to acquire images.
    
    ### Constructor Parameters:

    acq_settings: AcqSettings
        acquisition settings used in acquisition

    acq_dialog: AcqDialog
        acquisition dialog to provide updates during acquisition
        
    abort_flag: exceptions.AbortFlag
        flag to tell if user has aborted acquisition

    acq_directory: AcqDirectory
        acquisition directory which is updated throughout acquisition to match time point, fish and region.

    ### Child Classes:

    TimeSampAcquisition
        The default acquisition order. It takes does a full acquisition of all fish for each time point.

    SampTimeAcquisition
        Performs a full time series for each fish. Ie, if there are two fish in
        AcqSettings.fish_list and timepoints are enabled, a full time series will be performed for the
        first fish, and then once concluded, a full time series of the second fish will be acquired.

    PosTimeAcquisition
        Ie, if there is one fish with two regions AcqSettings.fish_list and timepoints are enabled, 
        a full time series will be performed for the first region, and then once concluded, a full 
        time series of the second region will be acquired.


    Abstract Methods:

    #### run()
        starts acquisition
    """
    #delay is pretty arbitrary. At the very least should be less than a second
    #to avoid inconsistent intervals between timepoints.
    TIME_DIALOG_UPDATE_DELAY_S = .01

    @abstractmethod
    def run(self):
        """
        starts acquisition
        """
        pass

    def __init__(self, acq_settings: AcqSettings, acq_dialog: AcqDialog,
                 abort_flag: exceptions.AbortFlag, acq_directory: AcqDirectory):
        self._logger = logging.getLogger(self._get_name())
        #deepcopy so that if GUI is changed during acquisition is in progress, won't change running acquisition
        self._acq_settings = acq_settings
        self._adv_settings = self._acq_settings.adv_settings
        self._acq_dialog = acq_dialog
        self._abort_flag = abort_flag
        self._acq_directory = acq_directory
        self.backup_used = False

    def _abort_check(self):
        #abort_check is called throughout acquisitions to check if the user has aborted the acquisition.
        if self._abort_flag.abort:
            raise exceptions.AbortAcquisitionException
        
    def _get_name(self) -> str:
        return self.__class__.__name__

    # time point helpers
    def _get_time(self) -> float:
        return time.time()
    
    def _get_time_since_start(self, start_time) -> float:
        return self._get_time() - start_time
    
    def _get_time_remaining(self, start_time) -> float:
        return self._acq_settings.time_points_interval_sec - self._get_time_since_start(start_time)
    
    def _get_minutes_left(self, start_time) -> tuple[int, int]:
        total_seconds_left = int(np.ceil(self._get_time_remaining(start_time)))
        return divmod(total_seconds_left, constants.S_IN_MIN)
    
    def _is_time_point_left(self, time_point) -> bool:
        if self._acq_settings.time_points_enabled:
            return self._acq_settings.num_time_points - time_point > 1
        else:
            return False
    
    def _wait_for_next_time_point(self, start_time):
        while self._get_time_remaining(start_time) > 0:
            self._abort_check()
            self._update_time_left(start_time)
            time.sleep(self.TIME_DIALOG_UPDATE_DELAY_S)
        while dir_functions.is_disk_writing(self._acq_directory.get_directory()):
            self._abort_check()
            self._update_acq_status("Finishing saving...")

    #run helpers
    def _acquire_regions(self, fish: Fish):
        for region_num, region in enumerate(fish.region_list):
            self._abort_check()
            if region.imaging_enabled:
                self._update_region_num(region_num)
                self._move_to_region(region)
                self._run_imaging_sequences(region)

    def _run_imaging_sequences(self, region: Region):
        self._abort_check()
        if region.snap_enabled:
            self._update_acq_status("Initializing Snap")
            self._acquire_imaging_sequence(Snap, region)

        self._abort_check()
        if region.video_enabled:
            self._update_acq_status("Initializing Video")
            if self._adv_settings.spectral_video_enabled:
                self._acquire_imaging_sequence(SpectralVideo, region)
            else:
                self._acquire_imaging_sequence(Video, region)

        self._abort_check()
        if region.z_stack_enabled:
            self._update_acq_status("Initializing Z Stack")
            if self._adv_settings.spectral_z_stack_enabled:
                self._acquire_imaging_sequence(SpectralZStack, region)
            else:
                self._acquire_imaging_sequence(ZStack, region)

    def _acquire_imaging_sequence(self, Sequence: ImagingSequence, region: Region):
        sequence = Sequence(region, self._acq_settings, self._abort_flag, self._acq_directory)
        for update_message in sequence.run():
            self._update_acq_status(update_message)

    def _move_to_region(self, region: Region):
        self._abort_check()
        self._update_acq_status("Moving to region")
        if region.z_stack_enabled and not (region.snap_enabled or region.video_enabled):
            Stage.move_stage(region.x_pos, region.y_pos, region.z_stack_start_pos)
        else:
            Stage.move_stage(region.x_pos, region.y_pos, region.z_pos)

    def _get_start_region(self, start_fish_num):
        for fish in self._acq_settings.fish_list[start_fish_num:]:
            if fish.imaging_enabled:
                for region in fish.region_list:
                    if region.imaging_enabled:
                        return region, self._acq_settings.fish_list.index(fish)
        else:
            return None, None
        
    def _acquire_end_videos(self, fish_nums: list[int] = [], region_num: int = 0):
        if self._adv_settings.end_videos_enabled:
            self._update_acq_status("taking end videos...")
            fish_list = [self._acq_settings.fish_list[num] for num in fish_nums] if fish_nums else self._acq_settings.fish_list
            for fish in fish_list:
                fish_num = self._acq_settings.fish_list.index(fish)
                if fish.imaging_enabled:
                    self._update_fish_label(fish_num)
                    region = deepcopy(fish.region_list[region_num])
                    region.video_enabled = True
                    region.video_exposure = self._adv_settings.end_videos_exposure
                    region.video_num_frames = self._adv_settings.end_videos_num_frames
                    region.video_channel_list = [BF_CHANNEL]
                    self._update_acq_status("moving to region...")
                    Stage.move_stage(region.x_pos, region.y_pos, region.z_pos)
                    acq_directory = deepcopy(self._acq_directory)
                    acq_directory.root = f"{acq_directory.root}/end_videos"
                    acq_directory.set_fish_num(fish_num)
                    acq_directory.set_region_num(region_num)
                    acq_directory.set_time_point(0)
                    video = Video(region, self._acq_settings, self._abort_flag, acq_directory)
                    for update_message in video.run():
                        self._update_acq_status(update_message)

    # directory methods
    def _update_directory(self, required_mb: float):
        if self._adv_settings.backup_directory_enabled and not self.backup_used:
            is_enough_space = dir_functions.is_enough_space(
                required_mb, self._adv_settings.backup_directory_limit, self._acq_directory.root)
            if not is_enough_space:
                self._acq_directory.set_root(self._adv_settings.backup_directory)
                self.backup_used = True

    # acq_dialog methods
    def _update_region_label(self, region_num):
        self._acq_dialog.region_label.setText(f"Region {region_num + 1}")

    def _update_fish_label(self, fish_num: int):
        self._acq_dialog.fish_label.setText(f"Fish {fish_num + 1}")

    def _update_time_point_label(self, time_point: int):
        self._acq_dialog.time_point_label.setText(f"Time Point {time_point + 1}")

    def _update_time_left(self, start_time):
        minutes_left, seconds_left = self._get_minutes_left(start_time)
        update_message = "next time point:"
        if minutes_left:
            update_message = f"{update_message} {minutes_left} minutes"
        update_message = f"{update_message} {seconds_left} seconds"
        self._acq_dialog.acq_label.setText(update_message)

    def _update_acq_status(self, message):
        """
        Displays message on acquisition label and writes it to logs
        """
        self._acq_dialog.acq_label.setText(message)
        self._logger.info(message)

    def _update_region_num(self, region_num):
        self._acq_directory.set_region_num(region_num)
        self._update_region_label(region_num)
        self._update_acq_status(f"Acquiring region {region_num + 1}")
    
    def _update_fish_num(self, fish_num):
        self._acq_directory.set_fish_num(fish_num)
        self._update_fish_label(fish_num)
        self._update_acq_status(f"Acquiring fish {fish_num + 1}")

    def _update_time_point_num(self, time_point_num):
        self._acq_directory.set_time_point(time_point_num)
        self._update_time_point_label(time_point_num)
        self._update_acq_status(f"Acquiring timepoint {time_point_num + 1}")


class TimeSampAcquisition(AcquisitionOrder):
    """
    TimeSampAcquisition is the default acquisition order. It takes does a full acquisition of all fish
    for each time point.

    Public Methods:

    #### run()
        runs acquisition
    """
    def run(self):
        start_region = self._get_start_region(0)[0]
        if not start_region:
            raise exceptions.AbortAcquisitionException("No region in list with imaging enabled")
        self._acquire_time_points(start_region)

    def _acquire_time_points(self, start_region):
        self._move_to_region(start_region)
        for time_point in range(self._acq_settings.num_time_points):
            start_time = self._get_time()
            self._update_time_point_num(time_point)
            self._acquire_fish()
            if self._is_time_point_left(time_point):
                self._move_to_region(start_region)
                self._wait_for_next_time_point(start_time)
            else:
                break
        self._acquire_end_videos()
        self._move_to_region(start_region)

    def _acquire_fish(self):
        for fish_num, fish in enumerate(self._acq_settings.fish_list):
            self._abort_check()
            if fish.imaging_enabled:
                self._update_directory(fish.size_mb)
                self._update_fish_num(fish_num)
                self._acquire_regions(fish)


class SampTimeAcquisition(AcquisitionOrder):
    """
    SampTimeAcquisition performs a full time series for each fish. Ie, if there are two fish in
    AcqSettings.fish_list and timepoints are enabled, a full time series will be performed for the
    first fish, and then once concluded, a full time series of the second fish will be acquired.

    Public Methods:

    #### run()
        runs acquisition
    """
    def run(self):
        if not self._get_start_region(0)[0]:
            raise exceptions.AbortAcquisitionException("No valid region for imaging")
        self._acquire_fish()

    def _acquire_fish(self):
        fish_num = 0
        while True:
            self._abort_check()
            start_region, fish_num = self._get_start_region(fish_num)
            if not start_region:
                break
            fish = self._acq_settings.fish_list[fish_num]
            self._update_fish_num(fish_num)
            self._move_to_region(start_region)
            self._acquire_time_points(fish, start_region)
            self._acquire_end_videos([fish_num])
            fish_num += 1

    def _acquire_time_points(self, fish: Fish, start_region: Region):
        for time_point in range(self._acq_settings.num_time_points):
            self._update_directory(fish.size_mb)
            start_time = self._get_time()
            self._update_time_point_num(time_point)
            self._acquire_regions(fish)
            if self._is_time_point_left(time_point):
                self._move_to_region(start_region)
                self._wait_for_next_time_point(start_time)
            else:
                break


class PosTimeAcquisition(AcquisitionOrder):
    """
    PosTimeAcquisition performs a full time series for each region. Ie, if there is one fish with two 
    regions AcqSettings.fish_list and timepoints are enabled, a full time series will be performed for 
    the first region, and then once concluded, a full time series of the second region will be acquired.

    Public Methods:

    #### run()
        runs acquisition
    """
    def run(self):
        if not self._get_start_region(0)[0]:
            raise exceptions.AbortAcquisitionException("No valid region for imaging")
        self._acquire_fish()

    def _acquire_fish(self):
        for fish in self._acq_settings.fish_list:
            self._acquire_regions(fish)

    def _acquire_regions(self, fish: Fish):
        for region_num, region in enumerate(fish.region_list):
            self._abort_check()
            if region.imaging_enabled:
                self._update_fish_num(self._acq_settings.fish_list.index(fish))
                self._update_region_num(region_num)
                self._move_to_region(region)
                self._acquire_time_points(region)
                self._acquire_end_videos([self._acq_settings.fish_list.index(fish)], region_num)

    def _acquire_time_points(self, region: Region):
        for time_point in range(self._acq_settings.num_time_points):
            self._update_directory(region.size_mb)
            start_time = self._get_time()
            self._update_time_point_num(time_point)
            self._run_imaging_sequences(region)
            if self._is_time_point_left(time_point):
                Stage.set_z_position(region.z_pos)
                self._wait_for_next_time_point(start_time)
            else:
                break
