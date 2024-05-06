import copy
import os
import time
import logging
from abc import ABC, abstractmethod

import numpy as np

from LS_Pycro_App.views import AcqDialog
from LS_Pycro_App.models.acq_settings import AcqSettings, HTLSSettings, Fish, Region
from LS_Pycro_App.models.acq_directory import AcqDirectory
from LS_Pycro_App.acquisition.imaging import ImagingSequence, Snap, Video, SpectralVideo, ZStack, SpectralZStack
from LS_Pycro_App.hardware import Stage, Camera, Pump, Valves
from LS_Pycro_App.utils import constants, dir_functions, exceptions, fish_detection, pycro, user_config
from LS_Pycro_App.utils.pycro import BF_CHANNEL, core

class AcquisitionSequence(ABC):
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
    # delay is pretty arbitrary. At the very least should be less than a second
    # to avoid inconsistent intervals between timepoints.
    TIME_DIALOG_UPDATE_DELAY_S = .01

    @abstractmethod
    def run(self):
        """
        starts acquisition
        """
        pass

    def __init__(self, acq_settings: AcqSettings | HTLSSettings, acq_dialog: AcqDialog,
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
                    region = copy.deepcopy(fish.region_list[region_num])
                    #Change private properties so default values in Region class attributes aren't modified
                    region._video_enabled = True
                    region._video_exposure = self._adv_settings.end_videos_exposure
                    region._video_num_frames = self._adv_settings.end_videos_num_frames
                    region._video_channel_list = [BF_CHANNEL]
                    self._update_acq_status("moving to region...")
                    Stage.move_stage(region.x_pos, region.y_pos, region.z_pos)
                    acq_directory = copy.deepcopy(self._acq_directory)
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
            if os.path.isdir(self._acq_directory.root):
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


class TimeSampAcquisition(AcquisitionSequence):
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


class SampTimeAcquisition(AcquisitionSequence):
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


class PosTimeAcquisition(AcquisitionSequence):
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


class HTLSSequence(AcquisitionSequence):
    _DETECT_TIMEOUT_S = 300
    _STD_THRESHOLD_FACTOR = 0.6
    _REGION_OVERLAP = 0.05
    _MAX_Z_STACK = 1200

    def run(self):
        self._acquire_fish()

    def _acquire_fish(self):
        Camera.set_binning(Camera.DEFAULT_BINNING)
        Camera.set_exposure(Camera.DETECTION_EXPOSURE)
        pycro.set_channel(pycro.GFP_CHANNEL)
        noise_image = self._get_snap_array()
        noise_thresh = np.mean(noise_image) - HTLSSequence._STD_THRESHOLD_FACTOR*np.std(noise_image)
        Camera.set_binning(Camera.DETECTION_BINNING)
        pycro.set_channel(pycro.BF_CHANNEL)
        bf_image = self._get_snap_array()
        fish_detect_thresh = np.mean(bf_image) - HTLSSequence._STD_THRESHOLD_FACTOR*np.std(bf_image)
        x_step_size = (1 - HTLSSequence._REGION_OVERLAP)*core.get_image_width()*core.get_pixel_size_um()
        fish_num = 0
        time_no_fish_s = 0
        start_pos = self._acq_settings.capillary_start_pos
        end_pos = self._acq_settings.capillary_end_pos
        while fish_num < self._acq_settings.num_fish:
            self._acq_directory.set_fish_num(fish_num + 1)
            self._update_acq_status("Initializing camera")
            Camera.set_binning(Camera.DETECTION_BINNING)
            Camera.set_exposure(Camera.DETECTION_EXPOSURE)
            pycro.set_channel(pycro.BF_CHANNEL)
            self._update_acq_status("Starting pump")
            #fill pump before so we don't have to query the pump while detecting
            #the fish
            Valves.open()
            Pump.fill()
            Pump.set_port("O")
            Pump.set_speed(Pump.DEFAULT_SPEED)
            Pump.set_velocity(Pump.DETECTION_VELOCITY)
            Pump.set_zero()
            self._update_acq_status("Waiting for fish")
            try:
                time_no_fish_s = self._wait_for_fish(fish_detect_thresh, time_no_fish_s)
            except exceptions.DetectionTimeoutException:
                break
            Valves.close()
            Pump.terminate()
            if not self._is_fish():
                continue
            try:
                self._update_acq_status("Finding fish position")
                x_offset = fish_detection.get_region_1_x_offset(start_pos, end_pos, x_step_size)
            except (exceptions.BubbleException, exceptions.WeirdFishException):
                continue
            time_no_fish_s = 0
            Camera.set_binning(Camera.DEFAULT_BINNING)
            dx = end_pos[0] - start_pos[0]
            dy = end_pos[1] - start_pos[1]
            dz = end_pos[2] - start_pos[2]
            x_stage_dir = 1 if start_pos[1] <= end_pos[0] else -1
            x_0 = start_pos[0] + x_stage_dir*abs(x_offset)
            init_factor = (x_0 - np.mean((start_pos[0], end_pos[0])))/dx + 0.5
            y_0 = init_factor*dy + start_pos[1]
            z_0 = init_factor*dz + start_pos[2]
            step_factor = x_step_size/abs(dx)
            x_incr = x_step_size*x_stage_dir
            y_incr = step_factor*dy
            z_incr = step_factor*dz
            for region_num, region in enumerate(self._acq_settings.fish_settings.region_list):
                self._update_region_label(region_num)
                region.x_pos = x_0 + region_num*x_incr
                region.y_pos = y_0 + region_num*y_incr
                region.z_pos = z_0 + region_num*z_incr
                self._move_to_region(region)
                if region.z_stack_enabled:
                    self._update_acq_status("Determining z-stack positions")
                    self._set_z_stack_pos(noise_thresh, region)
                self._acq_settings.fish_settings.region_list.append[region]
            self._run_imaging_sequences(region)
            self._acq_settings.fish_settings.write_to_config(fish_num + 1)
            fish_num += 1
        user_config.write_config_file(f"{self._acq_directory.root}/notes.txt")

    def _set_z_stack_pos(self, threshold, region: Region):
        if region.z_stack_channel_list:
            channel = self._get_max_channel(region)
            pycro.set_channel(channel)
            Stage.set_z_stage_speed(Stage._DEFAULT_STAGE_SPEED_UM_PER_S)
            for direction in [-1, 1]:
                max_z_pos = region.z_pos + direction*HTLSSequence._MAX_Z_STACK/2
                start_time = time.time()
                Stage.set_z_position(max_z_pos)
                core.stop_sequence_acquisition()
                core.start_continuous_sequence_acquisition(0)
                while True:
                    if core.get_remaining_image_count() > 0:
                        image = pycro.pop_next_image().get_raw_pixels()
                        if np.mean(image) < threshold:
                            Stage.halt()
                            if direction == -1:
                                region.z_stack_start_pos = Stage.get_z_position()
                            else:
                                region.z_stack_end_pos = Stage.get_z_position()
                            break
                        elif time.time() - start_time > HTLSSequence._MAX_Z_STACK/2/Stage._DEFAULT_STAGE_SPEED_UM_PER_S + 1:
                            if direction == -1:
                                region.z_stack_start_pos = max_z_pos
                            else:
                                region.z_stack_end_pos = max_z_pos
                        core.clear_circular_buffer()
                    else:
                        core.sleep(0.5)
                core.stop_sequence_acquisition()
    
    def _get_max_channel(self, region: Region):
        maxes = []
        for channel in region.z_stack_channel_list:
            pycro.set_channel(channel)
            image = self._get_snap_array()
            maxes.append(np.max(image))
        return region.z_stack_channel_list[np.argmax(maxes)]
    
    def _get_snap_array(self) -> np.ndarray:
        Camera.snap_image()
        return pycro.pop_next_image().get_raw_pixels()
    
    def _wait_for_fish(self, threshold, time_no_fish_s):
        core.stop_sequence_acquisition()
        core.start_continuous_sequence_acquisition(0)
        while True:
            if core.get_remaining_image_count() > 0:
                image = pycro.pop_next_image().get_raw_pixels()
                if np.mean(image) < threshold:
                    break
                elif time_no_fish_s > HTLSSequence._DETECT_TIMEOUT_S:
                    raise exceptions.DetectionTimeoutException
                time_no_fish_s += Camera.DETECTION_EXPOSURE*constants.MS_TO_S
                #clear buffer so that it doesn't fill. We're just analyzing the newest image
                #received so we don't need to be storing the other images.
                core.clear_circular_buffer()
            else:
                core.sleep(0.5)
        core.stop_sequence_acquisition()
        return time_no_fish_s
