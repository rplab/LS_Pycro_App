import copy
import time
import numpy as np
import logging
import pathlib
from abc import ABC, abstractmethod

from LS_Pycro_App.acquisition.views.py import AcqDialog
from LS_Pycro_App.htls_acquisition.models.htls_settings import HTLSSettings, Region, Fish
from LS_Pycro_App.acquisition.models.acq_directory import AcqDirectory
from LS_Pycro_App.acquisition.sequences.imaging import ImagingSequence, Snap, Video, SpectralVideo, ZStack, SpectralZStack
from LS_Pycro_App.hardware import Stage, Camera, Pump
from LS_Pycro_App.utils import dir_functions, exceptions, pycro, fish_detection, constants
from LS_Pycro_App.utils.pycro import core, studio


class HTLSSequence():
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

    Abstract Methods:

    #### run()
        starts acquisition
    """
    # delay is pretty arbitrary. At the very least should be less than a second
    # to avoid inconsistent intervals between timepoints.
    TIME_DIALOG_UPDATE_DELAY_S = .01
    _DETECT_TIMEOUT_S = 300
    _REGION_OVERLAP = 0.1

    @abstractmethod
    def run(self):
        """
        starts acquisition
        """
        pass

    def __init__(self, acq_settings: HTLSSettings, acq_dialog: AcqDialog,
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

    def _get_start_region(self, start_fish_num):
        for fish in self._acq_settings.fish_list[start_fish_num:]:
            if fish.imaging_enabled:
                for region in fish.region_list:
                    if region.imaging_enabled:
                        return region, self._acq_settings.fish_list.index(fish)
        else:
            return None, None

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

    def acquire_fish(self):
        Camera.set_binning(Camera.DETECTION_BINNING)
        Camera.set_exposure(Camera.DETECTION_EXPOSURE)
        bg_image = self._get_bg_image()
        bg_image_mean = np.mean(bg_image)
        bg_image_std = np.std(bg_image)
        x_step_size = (1-HTLSSequence._REGION_OVERLAP)*core.get_image_width()*core.get_pixel_size_um()
        fish_num = 0
        time_no_fish_s = 0
        while fish_num < self._acq_settings.num_fish:
            self._update_acq_status("Initializing camera")
            Camera.set_binning(Camera.DETECTION_BINNING)
            Camera.set_exposure(Camera.DETECTION_EXPOSURE)
            self._update_acq_status("Starting pump")
            Pump.set_port("O")
            Pump.set_speed(Pump.DEFAULT_SPEED)
            Pump.set_velocity(Pump.DETECTION_VELOCITY)
            Pump.set_zero()
            self._update_acq_status("Waiting for fish")
            while True:
                self._abort_check()
                Camera.snap_image()
                image = pycro.pop_next_image().get_raw_pixels()
                if fish_detection.fish_detected(image, bg_image_std, bg_image_mean):
                    self._update_acq_status("Fish found")
                    break
                else:
                    time.sleep(Camera.DETECTION_EXPOSURE)
                    time_no_fish_s += Camera.DETECTION_EXPOSURE*constants.MS_TO_S
                    if time_no_fish_s > HTLSSequence._DETECT_TIMEOUT_S:
                        raise exceptions.DetectionTimeoutException
            try:
                self._update_acq_status("Finding fish position")
                x_offset = fish_detection.get_region_1_x_offset(start_pos, end_pos, x_step_size)
            except (exceptions.BubbleException, exceptions.WeirdFishException):
                continue
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
            for region_num in range(self._acq_settings.num_regions):
                region = copy.deepcopy(self._acq_settings.region)
                region.x_pos = x_0 + region_num*x_incr
                region.y_pos = y_0 + region_num*y_incr
                region.z_pos = z_0 + region_num*z_incr
                Stage.set_x_position(region.x_pos)
                Stage.set_y_position(region.y_pos)
                Stage.get_z_position(region.z_pos)
                if region.z_stack_enabled:
                    self._update_acq_status("Determining z-stack positions")
                    self.set_z_stack_pos(region)
                self._run_imaging_sequences(region)
            self._acq_directory.set_fish_num(fish_num + 1)
            fish_num += 1

    def set_z_stack_pos(region: Region):
        if region.z_stack_channel_list:
            channel = region.z_stack_channel_list[0]
            pycro.set_channel(channel)


    def _get_bg_image(self) -> np.ndarray:
        Camera.snap_image()
        return pycro.pop_next_image().get_raw_pixels()
