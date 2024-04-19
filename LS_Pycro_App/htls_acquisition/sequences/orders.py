import time
import numpy as np
import logging
import pathlib
from abc import ABC, abstractmethod
from copy import deepcopy

from LS_Pycro_App.acquisition.views.py import AcqDialog
from LS_Pycro_App.acquisition.models.acq_settings import AcqSettings, Region
from LS_Pycro_App.acquisition.models.acq_directory import AcqDirectory
from LS_Pycro_App.acquisition.sequences.imaging import ImagingSequence, Snap, Video, SpectralVideo, ZStack, SpectralZStack
from LS_Pycro_App.hardware import Stage, Camera
from LS_Pycro_App.utils import dir_functions, exceptions, pycro, fish_detection
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
        fish_num = 0
        time_no_fish = 0
        Camera.set_binning(2)
        Camera.set_exposure(Camera.DETECTION_EXPOSURE)
        bg_image = self._get_bg_image()
        bg_image_mean = np.mean(bg_image)
        bg_image_std = np.std(bg_image)
        while fish_num < self._acq_settings.num_fish:
            pump.set_port(PumpPort.O)
            pump.set_speed(pump.ACQUIRE_SPEED)
            pump.set_zero()
            detect_start_time = time.time()
            while True:
                if not fish_detection.fish_detected():
                    time.sleep(Camera.DETECTION_EXPOSURE)
                elif time.time() - detect_start_time > HTLSSequence._DETECT_TIMEOUT_S:
                    raise exceptions.DetectionTimeoutException
                self._abort_check()
            fish_x_position = fish_detection.get_region_1_x()
            Stage.set_x_position(fish_x_position)
            self.rotate_fish()
            self.region.x_pos = Stage.get_x_position()
            self.region.y_pos = Stage.get_y_position()
            self.region.z_pos = Stage.get_z_position()
            self._acq_directory.set_fish_num(fish_num + 1)
            self._run_imaging_sequences(self.region)
            fish_num += 1

    def _get_bg_image(self) -> np.ndarray:
        Camera.snap_image()
        return pycro.pop_next_image().get_raw_pixels()
    
    def get_capillary_image(self):

        x_0 = -8320
        y_0 = -2443
        z_0 = -2642
        x_1 = 10237

        pixel_size = core.get_pixel_size_um()
        image_width_um = pixel_size*core.get_image_width()
        #0.90 provides 10% overlap for stitched image
        x_spacing = 0.9*image_width_um
        num_steps = int(np.ceil(np.abs((x_1-x_0)/x_spacing)))
        y_spacing = (y_1-y_0)/num_steps

        images = []
        positions = []
        for step_num in range(num_steps):
            x_pos = x_0 + x_spacing*step_num
            y_pos = y_0 + y_spacing*step_num
            positions.append((x_pos, y_pos))

            Stage.set_x_position(x_pos)
            Stage.set_y_position(y_0)
            Stage.set_z_position(z_0)
            Stage.wait_for_xy_stage()
            Stage.wait_for_z_stage()
            Camera.snap_image()
            image = pycro.pop_next_image().get_raw_pixels()
            images.append(image)
        
        return stitch.stitch_images(images, positions)
        
    
    def get_region_1_position(self, capillary_image):
        image = skimage.exposure.rescale_intensity(capillary_image)
        std = np.std(image)
        median = np.median(image)
        threshold = median - 1.5*std
        threshed = capillary_image < threshold
        #Area is somewhat arbitrary, but should be larger than "hole" caused by
        #bright pixels in swim bladder, usually around 10000
        filled = morphology.remove_small_holes(threshed, 10000)
        labeled = measure.label(filled)
        objects = [o for o in measure.regionprops(labeled) if o.eccentricity < 0.95 and o.area > 100000]
        centroids = [o.centroid for o in objects]
        #If more than just the eye and swim bladder are detected (ie, if fish is on its 
        #side and there are two eyes)
        if len(centroids) > 2:
            




    def remove_multiple_eyes(self):
        distance = 100
        while distance <= 300:
            while len(objects) > 2:
                centroids = []
                for o in objects:
                    for centroid in centroids:
                        #removes element if its x distance to other objects is small,
                        #ie if two eyes are next to each other
                        if abs(centroid[1] - o.centroid[1]) < distance:
                            objects.remove(o)
                    else:
                        centroids.append(o.centroid)
                distance += 25

    