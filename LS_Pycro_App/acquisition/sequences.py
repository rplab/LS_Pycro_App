import copy
import os
import time
import logging

import numpy as np

from LS_Pycro_App.acquisition.acq_gui import CLSAcqGui, HTLSAcqGui
from LS_Pycro_App.models.acq_settings import AcqSettings, HTLSSettings, Fish, Region
from LS_Pycro_App.models.acq_directory import AcqDirectory
from LS_Pycro_App.acquisition.imaging import ImagingSequence, Snap, Video, SpectralVideo, ZStack, SpectralZStack, DeconZStack
from LS_Pycro_App.hardware import Stage, Camera, Pump, Valves
from LS_Pycro_App.utils import constants, dir_functions, exceptions, fish_detection, pycro
from LS_Pycro_App.utils.pycro import BF_CHANNEL, core


class SequenceHelpers():
    """
    Class that holds many helpful functions for use in acquisition sequences. Inlcudes functions that
    update dialogs, check and wait for timepoints, moves stage regions, updates current save directory,
    and acquires end videos.
    
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
    """
    def __init__(self, acq_settings: AcqSettings | HTLSSettings, acq_gui: CLSAcqGui | HTLSAcqGui,
                 acq_directory: AcqDirectory, abort_flag: exceptions.AbortFlag, logger: logging.Logger):
        self._acq_settings = acq_settings
        self._adv_settings = self._acq_settings.adv_settings
        self._acq_gui = acq_gui
        self._acq_directory = acq_directory
        self._abort_flag = abort_flag
        self._logger = logger
        self.backup_used = False

    def _abort_check(self):
        #abort_check is called throughout acquisitions to check if the user has aborted the acquisition.
        if self._abort_flag.abort:
            raise exceptions.AbortAcquisitionException

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
            elif self._adv_settings.decon_z_stack_enabled:
                self._acquire_imaging_sequence(DeconZStack, region)
            else:
                self._acquire_imaging_sequence(ZStack, region)

    def _acquire_imaging_sequence(self, Sequence: ImagingSequence, region: Region):
        sequence = Sequence(region, self._acq_settings, self._acq_directory, self._abort_flag)
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
        self._acq_gui.region_update(region_num + 1)

    def _update_fish_label(self, fish_num: int):
        self._acq_gui.fish_update(fish_num + 1)

    def _update_acq_status(self, message):
        """
        Displays message on acquisition label and writes it to logs
        """
        self._acq_gui.status_update(message)
        self._logger.info(message)

    def _update_region_num(self, region_num):
        self._acq_directory.set_region_num(region_num)
        self._update_region_label(region_num)
        self._update_acq_status(f"Acquiring region {region_num + 1}")
    
    def _update_fish_num(self, fish_num):
        self._acq_directory.set_fish_num(fish_num)
        self._update_fish_label(fish_num)
        self._update_acq_status(f"Acquiring fish {fish_num + 1}")


class TimePointHelpers():
    # delay is pretty arbitrary. At the very least should be less than a second
    # to avoid inconsistent intervals between timepoints.
    TIME_DIALOG_UPDATE_DELAY_S = .01

    def __init__(self, acq_settings: AcqSettings | HTLSSettings, acq_gui: CLSAcqGui | HTLSAcqGui,
                 acq_directory: AcqDirectory, sequence_helpers: SequenceHelpers, logger: logging.Logger):
        self._acq_settings = acq_settings
        self._acq_gui = acq_gui
        self._acq_directory = acq_directory
        self._sequence_helpers = sequence_helpers
        self._logger = logger

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
            self._sequence_helpers._abort_check()
            self._update_time_left(start_time)
            time.sleep(self.TIME_DIALOG_UPDATE_DELAY_S)

    def _update_time_point_label(self, time_point: int):
        self._acq_gui.timepoint_update(time_point + 1)

    def _update_time_left(self, start_time):
        minutes_left, seconds_left = self._get_minutes_left(start_time)
        update_message = "next time point:"
        if minutes_left:
            update_message = f"{update_message} {minutes_left} minutes"
        update_message = f"{update_message} {seconds_left} seconds"
        #use status_update instead of update_acq_status because we don't want this
        #to fill up the logs
        self._acq_gui.status_update(update_message)

    def _update_time_point_num(self, time_point_num):
        self._acq_directory.set_time_point(time_point_num)
        self._update_time_point_label(time_point_num)
        self._sequence_helpers._update_acq_status(f"Acquiring timepoint {time_point_num + 1}")


class TimeSampAcquisition():
    """
    TimeSampAcquisition is the default acquisition order. It takes does a full acquisition of all fish
    for each time point.

    Public Methods:

    #### run()
        runs acquisition
    """
    def __init__(self, acq_settings: AcqSettings, acq_gui: CLSAcqGui,
                 acq_directory: AcqDirectory, abort_flag: exceptions.AbortFlag):
        self._logger = logging.getLogger(self.__class__.__name__)
        #deepcopy so that if GUI is changed during acquisition is in progress, won't change running acquisition
        self._acq_settings = acq_settings
        self._adv_settings = self._acq_settings.adv_settings
        self._acq_gui = acq_gui
        self._acq_directory = acq_directory
        self._abort_flag = abort_flag
        self._sequence_helpers = SequenceHelpers(self._acq_settings, self._acq_gui, self._acq_directory, self._abort_flag, self._logger)
        self._time_point_helpers = TimePointHelpers(self._acq_settings, self._acq_gui, self._acq_directory, self._sequence_helpers, self._logger)

    def run(self):
        start_region = self._sequence_helpers._get_start_region(0)[0]
        if not start_region:
            raise exceptions.AbortAcquisitionException("No region in list with imaging enabled")
        self._acquire_time_points(start_region)

    def _acquire_time_points(self, start_region):
        self._sequence_helpers._move_to_region(start_region)
        for time_point in range(self._acq_settings.num_time_points):
            start_time = self._time_point_helpers._get_time()
            self._time_point_helpers._update_time_point_num(time_point)
            self._acquire_fish()
            if self._time_point_helpers._is_time_point_left(time_point):
                self._sequence_helpers._move_to_region(start_region)
                self._time_point_helpers._wait_for_next_time_point(start_time)
            else:
                break
        self._sequence_helpers._acquire_end_videos()
        self._sequence_helpers._move_to_region(start_region)

    def _acquire_fish(self):
        for fish_num, fish in enumerate(self._acq_settings.fish_list):
            self._sequence_helpers._abort_check()
            if fish.imaging_enabled:
                self._sequence_helpers._update_directory(fish.size_mb)
                self._sequence_helpers._update_fish_num(fish_num)
                self._sequence_helpers._acquire_regions(fish)


class SampTimeAcquisition():
    """
    SampTimeAcquisition performs a full time series for each fish. Ie, if there are two fish in
    AcqSettings.fish_list and timepoints are enabled, a full time series will be performed for the
    first fish, and then once concluded, a full time series of the second fish will be acquired.

    Public Methods:

    #### run()
        runs acquisition
    """
    def __init__(self, acq_settings: AcqSettings, acq_gui: CLSAcqGui,
                 acq_directory: AcqDirectory, abort_flag: exceptions.AbortFlag):
        self._logger = logging.getLogger(self.__class__.__name__)
        #deepcopy so that if GUI is changed during acquisition is in progress, won't change running acquisition
        self._acq_settings = acq_settings
        self._adv_settings = self._acq_settings.adv_settings
        self._acq_gui = acq_gui
        self._acq_directory = acq_directory
        self._abort_flag = abort_flag
        self._sequence_helpers = SequenceHelpers(self._acq_settings, self._acq_gui, self._acq_directory, self._abort_flag, self._logger)
        self._time_point_helpers = TimePointHelpers(self._acq_settings, self._acq_gui, self._acq_directory, self._sequence_helpers, self._logger)

    def run(self):
        if not self._sequence_helpers._get_start_region(0)[0]:
            raise exceptions.AbortAcquisitionException("No valid region for imaging")
        self._acquire_fish()

    def _acquire_fish(self):
        fish_num = 0
        while True:
            self._sequence_helpers._abort_check()
            start_region, fish_num = self._sequence_helpers._get_start_region(fish_num)
            if not start_region:
                break
            fish = self._sequence_helpers._acq_settings.fish_list[fish_num]
            self._sequence_helpers._update_fish_num(fish_num)
            self._sequence_helpers._move_to_region(start_region)
            self._acquire_time_points(fish, start_region)
            self._sequence_helpers._acquire_end_videos([fish_num])
            fish_num += 1

    def _acquire_time_points(self, fish: Fish, start_region: Region):
        for time_point in range(self._acq_settings.num_time_points):
            self._sequence_helpers._update_directory(fish.size_mb)
            start_time = self._time_point_helpers._get_time()
            self._time_point_helpers._update_time_point_num(time_point)
            self._sequence_helpers._acquire_regions(fish)
            if self._time_point_helpers._is_time_point_left(time_point):
                self._sequence_helpers._move_to_region(start_region)
                self._time_point_helpers._wait_for_next_time_point(start_time)
            else:
                break


class PosTimeAcquisition():
    """
    PosTimeAcquisition performs a full time series for each region. Ie, if there is one fish with two 
    regions AcqSettings.fish_list and timepoints are enabled, a full time series will be performed for 
    the first region, and then once concluded, a full time series of the second region will be acquired.

    Public Methods:

    #### run()
        runs acquisition
    """
    def __init__(self, acq_settings: AcqSettings, acq_gui: CLSAcqGui,
                 acq_directory: AcqDirectory, abort_flag: exceptions.AbortFlag):
        self._logger = logging.getLogger(self.__class__.__name__)
        #deepcopy so that if GUI is changed during acquisition is in progress, won't change running acquisition
        self._acq_settings = acq_settings
        self._adv_settings = self._acq_settings.adv_settings
        self._acq_gui = acq_gui
        self._acq_directory = acq_directory
        self._abort_flag = abort_flag
        self._sequence_helpers = SequenceHelpers(self._acq_settings, self._acq_gui, self._acq_directory, self._abort_flag, self._logger)
        self._time_point_helpers = TimePointHelpers(self._acq_settings, self._acq_gui, self._acq_directory, self._sequence_helpers, self._logger)

    def run(self):
        if not self._sequence_helpers._get_start_region(0)[0]:
            raise exceptions.AbortAcquisitionException("No valid region for imaging")
        self._acquire_fish()

    def _acquire_fish(self):
        for fish in self._sequence_helpers._acq_settings.fish_list:
            self._acquire_regions(fish)

    def _acquire_regions(self, fish: Fish):
        for region_num, region in enumerate(fish.region_list):
            self._sequence_helpers._abort_check()
            if region.imaging_enabled:
                self._sequence_helpers._update_fish_num(self._acq_settings.fish_list.index(fish))
                self._sequence_helpers._update_region_num(region_num)
                self._sequence_helpers._move_to_region(region)
                self._acquire_time_points(region)
                self._sequence_helpers._acquire_end_videos([self._acq_settings.fish_list.index(fish)], region_num)

    def _acquire_time_points(self, region: Region):
        for time_point in range(self._acq_settings.num_time_points):
            self._sequence_helpers._update_directory(region.size_mb)
            start_time = self._time_point_helpers._get_time()
            self._time_point_helpers._update_time_point_num(time_point)
            self._sequence_helpers._run_imaging_sequences(region)
            if self._time_point_helpers._is_time_point_left(time_point):
                Stage.set_z_position(region.z_pos)
                self._time_point_helpers._wait_for_next_time_point(start_time)
            else:
                break


class HTLSSequence():
    _DETECT_TIMEOUT_S = 300
    _STITCH_STEP_SIZE_UM = 300
    _STITCH_IMAGE_WIDTH_UM = 11000
    _BF_THRESHOLD_FACTOR = 0.6
    _Z_STACK_THRESHOLD_FACTOR = 1.2
    _REGION_OVERLAP = 0.05
    _MAX_Z_STACK = 1000
    _FISH_SETTLE_PAUSE_S = 5
    _SET_Z_STACK_SPEED = 200

    def __init__(self, htls_settings: HTLSSettings, acq_gui: HTLSAcqGui,
                 acq_directory: AcqDirectory, abort_flag: exceptions.AbortFlag):
        self._logger = logging.getLogger(self.__class__.__name__)
        #deepcopy so that if GUI is changed during acquisition is in progress, won't change running acquisition
        self._htls_settings = htls_settings
        self._acq_gui = acq_gui
        self._acq_directory = acq_directory
        self._abort_flag = abort_flag
        self._acq_settings = self._htls_settings.acq_settings
        self._adv_settings = self._acq_settings.adv_settings
        self._sequence_helpers = SequenceHelpers(self._acq_settings, self._acq_gui, self._acq_directory, self._abort_flag, self._logger)

    def run(self):
        self._htls_settings.remove_fish_sections()
        start_pos = self._htls_settings.start_pos
        std_detect, mean_detect = self._get_fish_detect_stats()
        z_stack_thresh = self._get_z_stack_thresh()
        fish_num = 0
        time_no_fish_s = 0
        while fish_num < self._htls_settings.num_fish:
            try:
                self._sequence_helpers._abort_check()
                Stage.move_stage(*self._htls_settings.start_pos)
                time_no_fish_s = self._wait_for_fish(std_detect, mean_detect, time_no_fish_s)
            except exceptions.DetectionTimeoutException:
                break
            self._sequence_helpers._update_acq_status("Determining fish position")
            try:
                x_offset = fish_detection.get_region_1_x_offset(start_pos, self._get_end_pos(), HTLSSequence._STITCH_STEP_SIZE_UM, fish_num)
            except ValueError:
                continue
            time_no_fish_s = 0
            #copy fish so fish settings aren't modified
            fish = copy.deepcopy(self._htls_settings.fish_settings)
            self._htls_settings.fish_list.append(fish)
            self._set_region_positions(fish, start_pos, x_offset, z_stack_thresh)
            self._acquire_fish(fish, fish_num)
            if self._adv_settings.end_videos_enabled:
                self._sequence_helpers._acquire_end_videos([fish_num])
            fish_num += 1

    def _acquire_fish(self, fish: Fish, fish_num: int):
        Camera.set_binning(Camera.DEFAULT_BINNING)
        self._sequence_helpers._update_directory(fish.size_mb)
        self._acq_directory.set_fish_num(fish_num)
        self._sequence_helpers._acquire_regions(fish)
        fish.write_to_config(fish_num) 

    def _get_end_pos(self):
        end_pos = copy.deepcopy(self._htls_settings.start_pos)
        end_pos[0] += HTLSSequence._STITCH_IMAGE_WIDTH_UM
        return end_pos

    def _get_fish_detect_stats(self):
        Camera.set_binning(Camera.DETECTION_BINNING)
        Camera.set_exposure(Camera.DETECTION_EXPOSURE)
        pycro.set_channel(pycro.BF_CHANNEL)
        bf_image = self._get_snap_array()
        return np.std(bf_image), np.mean(bf_image)
    
    def _get_max_channel(self, region: Region):
        maxes = []
        for channel in region.z_stack_channel_list:
            pycro.set_channel(channel)
            image = self._get_snap_array()
            maxes.append(np.max(image))
        return region.z_stack_channel_list[np.argmax(maxes)]
    
    def _get_region_distance(self):
        return (1 - HTLSSequence._REGION_OVERLAP)*core.get_image_width()*core.get_pixel_size_um()
    
    def _get_snap_array(self) -> np.ndarray:
        """
        Snaps image and returns it as ndarray
        """
        Camera.snap_image()
        return pycro.pop_next_image().get_raw_pixels()
    
    def _get_z_stack_thresh(self):
        """
        Takes GFP image with no fish in field of view to determine background statistics, 
        then returns threshold based on statistics to be used in determining
        z-stack positions. Currently, uses standard deviation multiplied by a small factor.
        """
        pycro.set_channel(pycro.GFP_CHANNEL)
        gfp_image = self._get_snap_array()
        return HTLSSequence._Z_STACK_THRESHOLD_FACTOR*np.std(gfp_image)
    
    def _start_pump(self):
        Valves.open()
        Pump.fill()
        Pump.set_port("O")
        Pump.set_speed(Pump.DEFAULT_SPEED)
        Pump.set_velocity(Pump.DETECTION_VELOCITY)
        Pump.set_zero()

    def _set_region_positions(self, fish: Fish, start_pos: tuple[int], x_offset: float, std_z_stack: float):
        for region_num, region in enumerate(fish.region_list):
            self._sequence_helpers._update_acq_status(f"Moving to region {region_num + 1}")
            region.x_pos, region.y_pos, region.z_pos = start_pos
            region.x_pos += x_offset - region_num*self._get_region_distance()
            self._sequence_helpers._move_to_region(region)
            if region.z_stack_enabled:
                self._sequence_helpers._update_acq_status(f"Determining region {region_num + 1} z-stack positions")
                self._set_z_stack_pos(region, std_z_stack)

    def _set_z_stack_pos(self, region: Region, threshold):
        if region.z_stack_channel_list:
            pycro.set_channel(region.z_stack_channel_list[0])
            for direction in [-1, 1]:
                Stage.set_z_position(region.z_pos)
                Stage.wait_for_z_stage()
                max_z_pos = region.z_pos + direction*HTLSSequence._MAX_Z_STACK/2
                start_time = time.time()
                core.stop_sequence_acquisition()
                core.start_continuous_sequence_acquisition(0)
                Stage.set_z_at_speed(max_z_pos, HTLSSequence._SET_Z_STACK_SPEED)
                while True:
                    if core.get_remaining_image_count() > 0:
                        self._sequence_helpers._abort_check()
                        image = pycro.pop_next_image().get_raw_pixels()
                        if np.std(image) <= threshold:
                            Stage.halt()
                            break
                        #If stage is reaches the end position without reaching threshold
                        elif time.time() - start_time > HTLSSequence._MAX_Z_STACK/2/HTLSSequence._SET_Z_STACK_SPEED + 0.5:
                            break
                        else:
                            core.sleep(0.5)
                        core.clear_circular_buffer()
                core.stop_sequence_acquisition()
                if direction == -1:
                    region.z_stack_start_pos = Stage.get_z_position()
                else:
                    region.z_stack_end_pos = Stage.get_z_position()
    
    def _wait_for_fish(self, std_detect, mean_detect, time_no_fish_s):
        self._sequence_helpers._update_acq_status("Initializing wait for fish")
        #initialize camera to detection settings
        Camera.set_binning(Camera.DETECTION_BINNING)
        Camera.set_exposure(Camera.DETECTION_EXPOSURE)
        pycro.set_channel(pycro.BF_CHANNEL)
        #begins the pumping of the fish
        self._start_pump()
        self._sequence_helpers._update_acq_status("Waiting for fish")
        core.stop_sequence_acquisition()
        core.start_continuous_sequence_acquisition(0)
        start_time = time.time()
        while True:
            total_time_s = time_no_fish_s + time.time() - start_time
            if core.get_remaining_image_count() > 0:
                self._sequence_helpers._abort_check()
                mm_image = pycro.pop_next_image()
                image = mm_image.get_raw_pixels()
                if np.std(image) > 1.1*std_detect and np.mean(image) < 0.8*mean_detect:
                    data = pycro.MultipageDatastore(fr"E:\HTLS Test\fish detection")
                    data.put_image(mm_image)
                    data.close()
                    break
                elif total_time_s > HTLSSequence._DETECT_TIMEOUT_S:
                    raise exceptions.DetectionTimeoutException
                #clear buffer so that it doesn't fill. We're just analyzing the newest image
                #received so we don't need to be storing the images.
                core.clear_circular_buffer()
            else:
                core.sleep(0.5)
        core.stop_sequence_acquisition()
        #Valves closing first here is important because it instantly stops the fish.
        Valves.close()
        Pump.terminate()
        self._sequence_helpers._update_acq_status("Waiting for fish to settle")
        time.sleep(HTLSSequence._FISH_SETTLE_PAUSE_S)
        return total_time_s
