"""
This module holds all the imaging sequences . All of these are essentially adapted scripts
from the Beanshell scripting panel in Micro-Manager. 

The non-underscored methods are image acquisition scripts that are meant to be accessed only by acquisition_classes.
Attempting to use these methods without the acquisition class will not work correctly as some vital hardware 
initialization is missing.

Please see the developer's guide for more information on these scripts.

Notes:

- The "yield" keyword is used throughout to provide update messages. This is mostly used in the 
Acquisition class method status_update() which updates the logs and acquisition dialog window.
I don't think this is a standard pattern at all but it seems to work well here.

- All exceptions in this class are reraised. This is because some objects (like the datastore) need to be closed before
the more general exception handling (found in acquisition_class) is called.

- Essentially, any hardware method that applies to all regions (such as moving the stage to the position in Region) and
all methods that rely on an instance of AcquisitionSettings should be set in acquisition_classes, not here.
"""

import logging
import os
import shutil
from abc import ABC, abstractmethod
import time

import numpy as np

import LS_Pycro_App.hardware.camera
from LS_Pycro_App.models.acq_settings import AcqSettings, Region
from LS_Pycro_App.models.acq_directory import AcqDirectory
from LS_Pycro_App.hardware import Camera, Plc, Stage, Galvo
from LS_Pycro_App.hardware.camera import Hamamatsu2, select_multi_camera
from LS_Pycro_App.controllers.select_controller import microscope, MicroscopeConfig
from LS_Pycro_App.utils import acq_record, constants, dir_functions, exceptions, pycro, general_functions
from LS_Pycro_App.utils.pycro import core

_logger = logging.getLogger(__name__)

#Channels that are acquired with both Klamath cameras at once (via the Micro-Manager MultiCamera device).
#The channel name alone decides this; there is no separate dual-camera setting. Images from the second
#camera are saved in a parallel "<acq type>_cam2" folder (see AcqDirectory.get_directory_cam2()).
#Dual-camera acquisition is supported in Snap, Video and ZStack. Spectral and decon sequences always use
#a single camera.
DUAL_CAMERA_CHANNELS = ("488 Dual", "Dual Excitation")


def is_dual_camera_channel(channel: str) -> bool:
    return microscope == MicroscopeConfig.KLAMATH and channel in DUAL_CAMERA_CHANNELS


class ImagingSequence(ABC):
    SINGLE_SAVE_IMAGE_LIMIT = 10000
    WAIT_FOR_IMAGE_MS = 2
    CAMERA_TIMEOUT_MS = 2000
    ATTEMPT_LIMIT = 2
    """
    Base class for all imaging sequences (such as z-stacks, videos, snaps). 
    
    Imaging sequences typically either work by taking multiple single images or taking continuous sequences of images. 
    For the former (for snaps and spectral images), sequence should utilize the _snap_image() method to capture images. 
    For the latter, use the_start_sequence_acquisition() method combined with _wait_for_sequence_images() to retrieve 
    and save images.

    ###abstract methods:

    _set_summary_metadata()
        Creates the summary metadata and sets it as the current datastore's summary metadata. Read docstring and MM
        documentation found in utils.pycro summary_metadata_builder

    _pop_image_with_metadata()
        pops the next image from the MM circular buffer, grabs its metadata, updates its metadata, 
        and then returns image with the updated metadata.

    _acquire_images
        creates datastore, acquires all images in sequence, places them into the datastore, then closes datastore.
    """
    @abstractmethod
    def _set_summary_metadata(self, channels: str | list):
        """
        Creates the summary metadata and sets it as the current datastore's summary metadata
        """
        pass

    @abstractmethod
    def _pop_image_with_metadata(self, frame_num: int, channel_num: int = 0, image = None):
        """
        pops the next image from the MM circular buffer (unless an already-popped image is given), grabs its
        metadata, updates its metadata, and then returns image with the updated metadata.

        channel_num is defaulted to 0 because generally channels are acquired and saved separately
        from one another. Thus, since there is only ever one channel in the image stack, the channel
        should be set to 0.
        """
        pass
    
    @abstractmethod
    def _acquire_images(self):
        """
        creates datastore, acquires all images in sequence, places them into the datastore, then closes datastore.
        Should call _pre_acquisition_hardware_init() at the beginning.
        """
        pass
    
    def __init__(self, region: Region, acq_settings: AcqSettings, acq_directory: AcqDirectory, abort_flag: exceptions.AbortFlag):
        self._region = region
        self._acq_settings = acq_settings
        self._adv_settings = acq_settings.adv_settings
        self._acq_directory = acq_directory
        self._abort_flag = abort_flag
        self._datastore = None
        #datastore for the second camera; only used for dual-camera channels
        self._datastore2 = None
        #True while acquiring a dual-camera channel (see is_dual_camera_channel())
        self._dual_camera = False
        #dual-camera state the hardware was last initialized for (None = not yet initialized)
        self._hardware_dual_state = None

    def run(self):
        for update_message in self._acquire_images():
            yield update_message

    def _get_name(self):
        return self.__class__.__name__.lower()

    def _get_num_frames(self):
        """
        Number of frames per camera in a sequence acquisition (used to discard surplus dual-camera frames).
        """
        return self._region.z_stack_num_frames

    def _create_datastore_with_summary(self, channels: str | list):
        self._acq_directory.set_acq_type(f"{self._get_name()}/{channels}".replace(",",""))
        self._datastore = pycro.MultipageDatastore(self._acq_directory.get_directory())
        if self._dual_camera:
            self._datastore2 = pycro.MultipageDatastore(self._acq_directory.get_directory_cam2())
        else:
            self._datastore2 = None
        self._set_summary_metadata(channels)

    def _set_summary_metadata_all(self, summary):
        """
        Sets summary metadata on the datastore, and on the second camera's datastore if there is one.
        """
        self._datastore.set_summary_metadata(summary)
        if self._datastore2:
            self._datastore2.set_summary_metadata(summary)

    def _close_and_move_files(self):
        self._datastore.close_and_move_files()
        if self._datastore2:
            self._datastore2.close_and_move_files()

    def _close_and_delete_files(self):
        """
        Closes datastore(s) and deletes their images (used before reattempting a failed sequence).
        Deletes the folders the datastores actually wrote to.
        """
        for datastore in (self._datastore, self._datastore2):
            if datastore:
                datastore.close()
                if os.path.isdir(datastore.save_path):
                    shutil.rmtree(datastore.save_path)

    def _abort_check(self):
        if self._abort_flag.abort:
            if self._datastore:
                self._close_and_move_files()
            raise exceptions.AbortAcquisitionException

    def _init_hardware_for_channel(self, channel: str, exposure, force: bool = False):
        """
        Sets self._dual_camera for channel and (re)initializes hardware if the dual-camera state changed
        (or if force is True, e.g. when reattempting after a camera timeout changed the PLC).
        """
        self._dual_camera = is_dual_camera_channel(channel)
        if force or self._dual_camera != self._hardware_dual_state:
            self._pre_acquisition_hardware_init(exposure)
            self._hardware_dual_state = self._dual_camera
        
    def _pre_acquisition_hardware_init(self, exposure):
        Camera.set_exposure(exposure)
        if self._dual_camera:
            Hamamatsu2.set_exposure(exposure)
        if Camera == LS_Pycro_App.hardware.camera.Hamamatsu:
            if Galvo and Galvo.settings.is_lsrm:
                framerate = general_functions.exposure_to_frequency(exposure)
                Galvo.settings.lsrm_framerate = min(framerate, Camera.LSRM_MAX_FRAMERATE)
                Galvo.set_lsrm_mode()
                Plc.set_continuous_pulses(framerate)
                Camera.set_lsrm_mode(Galvo.settings.lsrm_ili, Galvo.settings.lsrm_num_lines)
                if self._dual_camera:
                    Hamamatsu2.set_lsrm_mode(Galvo.settings.lsrm_ili, Galvo.settings.lsrm_num_lines)
            elif self._dual_camera:
                #Both cameras are triggered by the same PLC pulses (via the DAQ) so their frames are
                #simultaneous. In synchronous-readout mode the exposure equals the interval between trigger
                #pulses, so the PLC rate is set from the requested exposure. (Previously dual-camera snaps
                #used a fixed 30 Hz, and videos used whatever rate the PLC was last left at.)
                Camera.set_sync_readout_mode()
                Hamamatsu2.set_sync_readout_mode()
                Plc.set_continuous_pulses(general_functions.exposure_to_frequency(exposure))
            else:
                Camera.set_burst_mode()

    def _snap_image(self, frame_num: int, channel_num: int = 0):
        """
        snaps a single image (one from each camera for dual-camera channels) and puts it in datastore(s)
        """
        if self._dual_camera:
            self._snap_dual_camera_image(frame_num, channel_num)
        else:
            Camera.snap_image()
            image = self._pop_image_with_metadata(frame_num, channel_num)
            self._datastore.put_image(image)

    def _snap_dual_camera_image(self, frame_num: int, channel_num: int = 0):
        """
        Takes one image with each Klamath camera simultaneously using the MultiCamera device. The cameras
        are in synchronous-readout mode, triggered by the PLC (set in _pre_acquisition_hardware_init()).
        Gives up after exposure + Camera.SNAP_TIMEOUT_MARGIN_S, like Camera.snap_image().
        """
        core.stop_sequence_acquisition()
        core.clear_circular_buffer()
        Camera.select()
        exposure_ms = core.get_exposure()
        select_multi_camera()
        core.start_sequence_acquisition(1, 0, True)
        deadline = time.monotonic() + exposure_ms*constants.MS_TO_S + Camera.SNAP_TIMEOUT_MARGIN_S
        while core.get_remaining_image_count() < 2:
            if time.monotonic() > deadline:
                core.stop_sequence_acquisition()
                Camera.select()
                raise exceptions.CameraTimeoutException(
                    f"Dual-camera snap timed out: fewer than 2 images within {exposure_ms} ms exposure "
                    f"+ {Camera.SNAP_TIMEOUT_MARGIN_S} s")
            core.sleep(ImagingSequence.WAIT_FOR_IMAGE_MS)
        core.stop_sequence_acquisition()
        for _ in range(2):
            raw_image, camera_label = pycro.pop_next_image_with_camera_tag()
            image = self._pop_image_with_metadata(frame_num, channel_num, image=raw_image)
            if camera_label == Camera.CAM_NAME:
                self._datastore.put_image(image)
            else:
                self._datastore2.put_image(image)
        Camera.select()

    def _start_sequence_acquisition(self, num_frames: int):
        if self._dual_camera:
            select_multi_camera()
            #As on the Klamath computer: twice the number of frames is requested from the MultiCamera device,
            #and surplus frames beyond num_frames per camera are discarded in _wait_for_sequence_images().
            core.start_sequence_acquisition(num_frames*2, 0, True)
        else:
            #Camera.start_sequence_acquisition() also makes Camera the active camera again
            Camera.start_sequence_acquisition(num_frames)

    def _wait_for_sequence_images(self):
        """
        Image saving loop. This is a more advanced implementation of an example burst acquisition script on
        the Micro-Manager website.

        current_frame keeps track of current frame/slice for metadata
       
        time_no_image is the time without the core receiving an image. If this exceeds the CAMERA_TIMEOUT_MS constant,
        the current acquisition will end and the camera_timeout_response() method will be called.

        is_saving is set to True when sequence acquisition is over but there are still images in the buffer
        """
        current_frame = 0
        #frame counter for the second camera (dual-camera channels only)
        cam2_frame = 0
        time_no_image = 0
        is_saving = False
        while core.get_remaining_image_count() > 0 or core.is_sequence_running():
            if core.get_remaining_image_count() > 0:
                self._abort_check()
                if self._dual_camera:
                    raw_image, camera_label = pycro.pop_next_image_with_camera_tag()
                    if camera_label == Camera.CAM_NAME:
                        if current_frame < self._get_num_frames():
                            image = self._pop_image_with_metadata(frame_num=current_frame, image=raw_image)
                            self._datastore.put_image(image)
                        current_frame += 1
                    else:
                        if cam2_frame < self._get_num_frames():
                            image = self._pop_image_with_metadata(frame_num=cam2_frame, image=raw_image)
                            self._datastore2.put_image(image)
                        cam2_frame += 1
                else:
                    image = self._pop_image_with_metadata(frame_num=current_frame)
                    self._datastore.put_image(image)
                    current_frame += 1
                time_no_image = 0
                if not (core.is_sequence_running() or is_saving):
                    yield f"Saving {self._get_name()}"
                    is_saving = True
            elif time_no_image >= ImagingSequence.CAMERA_TIMEOUT_MS:
                raise exceptions.CameraTimeoutException
            else:
                core.sleep(self.WAIT_FOR_IMAGE_MS)
                time_no_image += self.WAIT_FOR_IMAGE_MS
        if self._dual_camera:
            _logger.info(f"Dual-camera sequence: {current_frame} frames from camera 1, {cam2_frame} from camera 2 "
                         f"({self._get_num_frames()} kept per camera)")

    def _camera_timeout_response(self):
        """
        Sequence acquisitions are prone to camera timeouts if the core doesn't receive enough images. Unfortunately,
        if this happens, MM will just freeze up, and so custom implementation is required to get through a camera
        timeout.
        """
        #Camera times out because it's expecting a certain number of pulses, and it if it doesn't receive them,
        #it freezes up. Plc is set to pulse so it unfreezes the camera, allowing us to stop the sequence acquisition.
        Plc.set_continuous_pulses(20)
        core.stop_sequence_acquisition()
        core.clear_circular_buffer()
        self._datastore.close()
        if self._datastore2:
            self._datastore2.close()


class Snap(ImagingSequence):
    """
    Simple snap acquisition. Takes a single image with each channel.
    """
    def _pop_image_with_metadata(self, frame_num: int, channel_num: int = 0, image = None):
        image = pycro.pop_next_image() if image is None else image
        coords = pycro.ImageCoordsBuilder().t(frame_num).build()
        meta = pycro.ImageMetadataBuilder(image).x(self._region.x_pos).y(
            self._region.y_pos).z(self._region.z_pos).build()
        return image.copy_with(coords, meta)
    
    def _set_summary_metadata(self, channel):
        summary = pycro.SummaryMetadataBuilder().channel_list(channel).build()
        self._set_summary_metadata_all(summary)

    def _acquire_images(self):
        self._abort_check()
        for channel in self._region.snap_channel_list:
            self._abort_check()
            yield f"Acquiring {channel} {self._get_name()}"
            self._init_hardware_for_channel(channel, self._region.snap_exposure)
            self._create_datastore_with_summary(channel)
            pycro.set_channel(channel)
            self._snap_image(0)
            self._close_and_move_files()


class Video(ImagingSequence):
    """
    Standard video. Takes a continuous video with region.video_num_frames with each channel provided.
    """
    def _set_summary_metadata(self, channel):
        summary_builder = pycro.SummaryMetadataBuilder().t(self._region.video_num_frames)
        summary_builder = summary_builder.channel_list(channel)
        summary_builder = summary_builder.interval_ms(self._region.video_exposure)
        self._set_summary_metadata_all(summary_builder.build())

    def _pop_image_with_metadata(self, frame_num: int, channel_num: int = 0, image = None):
        image = pycro.pop_next_image() if image is None else image
        coords = pycro.ImageCoordsBuilder().t(frame_num).build()
        meta = pycro.ImageMetadataBuilder(image).x(self._region.x_pos).y(
            self._region.y_pos).z(self._region.z_pos).build()
        return image.copy_with(coords, meta)

    def _get_num_frames(self):
        return self._region.video_num_frames

    def _acquire_images(self):
        """
        Acquire image method for sequence acquisitions. Current sequence acquisitions iterate through channels,
        creating a separate datastore for each channel, sets summary metadata, begins sequence acquisition, and then
        writes images. This is why this general implementation is possible.
       
        I can't see a future where sequence acquisitions don't follow this pattern, but if it happens, a different
        implementation will have to be written.
        """
        for channel in self._region.video_channel_list:
            attempt_num = 0
            while attempt_num < ImagingSequence.ATTEMPT_LIMIT:
                self._abort_check()
                yield f"Acquiring {channel} {self._get_name()}"
                #On a reattempt, hardware is re-initialized because _camera_timeout_response() leaves the PLC
                #pulsing at 20 Hz, which would otherwise set the frame rate of LSRM and dual-camera videos.
                #(Exposure is z_stack_exposure, as in the original code.)
                self._init_hardware_for_channel(channel, self._adv_settings.z_stack_exposure, force=attempt_num > 0)
                pycro.set_channel(channel)
                self._create_datastore_with_summary(channel)
                self._start_sequence_acquisition(self._region.video_num_frames)
                try:
                    for update_message in self._wait_for_sequence_images():
                        yield update_message
                except exceptions.CameraTimeoutException:
                    acq_record.report("camera_timeout", f"{self._get_name()} {channel}, attempt {attempt_num + 1}")
                    #upon camera timeout exception, reattempts until attempt_num == attempt limit
                    self._camera_timeout_response()
                    attempt_num += 1
                    if attempt_num < ImagingSequence.ATTEMPT_LIMIT:
                        #deletes images, unless it's the final attempt
                        self._close_and_delete_files()
                else:
                    self._close_and_move_files()
                    #breaks upon success
                    break


class SpectralVideo(Video):
    """
    Video that switches between channels every image. Video finishes when there
    are region.video_num_images images of each channel.
    """
    def _set_summary_metadata(self, channel):
        summary_builder = pycro.SummaryMetadataBuilder().channel_list(channel)
        summary_builder = summary_builder.t(self._region.video_num_frames)
        summary_builder = summary_builder.interval_ms(self._region.video_exposure)
        self._set_summary_metadata_all(summary_builder.build())

    def _pop_image_with_metadata(self, frame_num: int, channel_num: int = 0, image = None):
        image = pycro.pop_next_image() if image is None else image
        coords = pycro.ImageCoordsBuilder().c(channel_num).t(frame_num).build()
        meta = pycro.ImageMetadataBuilder(image).x(self._region.x_pos).y(
            self._region.y_pos).z(self._region.z_pos).build()
        return image.copy_with(coords, meta)

    def _acquire_images(self):
        self._pre_acquisition_hardware_init(self._region.video_exposure)
        yield f"Acquiring {self._get_name()}"
        self._create_datastore_with_summary(self._region.video_channel_list)
        current_frame = 0
        while current_frame < self._region.video_num_frames:
            for channel_num, channel in enumerate(self._region.video_channel_list):
                self._abort_check()
                pycro.set_channel(channel)
                self._snap_image(current_frame, channel_num)
            current_frame += 1
        self._close_and_move_files()


class ZStack(ImagingSequence):
    """
    Z-Stack works by setting camera to external trigger mode, setting the stage to scan, and then
    having the PLC trigger the camera at specific intervals to acquire images. Because of this,
    Z-Stack requires the PLC and stage scan to be initialized before acquisition begins.
    Then, the sequence acquisition is started, the stage starts scanning, and images are collected.
    """
    def _pre_acquisition_hardware_init(self, exposure):
        Camera.set_exposure(exposure)
        if microscope == MicroscopeConfig.KLAMATH or microscope == MicroscopeConfig.HTLS:
            if self._dual_camera:
                Hamamatsu2.set_exposure(exposure)
            if Galvo.settings.is_lsrm:
                framerate = general_functions.exposure_to_frequency(exposure)
                Galvo.settings.lsrm_framerate = min(framerate, Camera.LSRM_MAX_FRAMERATE)
                Galvo.set_lsrm_mode()
                Plc.set_for_z_stack(self._region.z_stack_step_size, self._adv_settings.z_stack_stage_speed)
                Camera.set_lsrm_mode(Galvo.settings.lsrm_ili, Galvo.settings.lsrm_num_lines)
                if self._dual_camera:
                    Hamamatsu2.set_lsrm_mode(Galvo.settings.lsrm_ili, Galvo.settings.lsrm_num_lines)
            elif self._adv_settings.edge_trigger_enabled or self._region.z_stack_step_size > 1:
                Camera.set_edge_trigger_mode()
                if self._dual_camera:
                    Hamamatsu2.set_edge_trigger_mode()
            else:
                Camera.set_sync_readout_mode()
                if self._dual_camera:
                    Hamamatsu2.set_sync_readout_mode()
        elif microscope == MicroscopeConfig.WILLAMETTE:
            if Camera == LS_Pycro_App.hardware.camera.Pco:
                Camera.set_ext_trig_mode()
            elif self._adv_settings.edge_trigger_enabled or self._region.z_stack_step_size > 1:
                #Edge trigger caps exposure below the frame interval, so it's only used when a
                #custom (shorter) exposure is wanted. See Camera.get_max_edge_trigger_exposure().
                Camera.set_edge_trigger_mode()
            else:
                Camera.set_sync_readout_mode()

    def _camera_timeout_response(self):
        #calls default camera reset function from super class
        super()._camera_timeout_response()
        Plc.set_for_z_stack(self._region.z_stack_step_size, self._adv_settings.z_stack_stage_speed)

    def _set_summary_metadata(self, channel):
        summary_builder = pycro.SummaryMetadataBuilder().z(self._region.z_stack_num_frames).step(
            self._region.z_stack_step_size)
        summary_builder = summary_builder.channel_list(channel).step(self._region.z_stack_step_size)
        self._set_summary_metadata_all(summary_builder.build())

    def _pop_image_with_metadata(self, frame_num: int, channel_num: int = 0, image = None):
        image = pycro.pop_next_image() if image is None else image
        coords = pycro.ImageCoordsBuilder().z(frame_num).build()
        meta = pycro.ImageMetadataBuilder(image).x(self._region.x_pos).y(self._region.y_pos).z(
            self._calculate_z_pos(frame_num)).build()
        return image.copy_with(coords, meta)
        
    def _calculate_z_pos(self, slice_num: int):
        if self._region.z_stack_start_pos <= self._region.z_stack_end_pos:
            z_pos = self._region.z_stack_start_pos + self._region.z_stack_step_size*slice_num
        else:
            z_pos = self._region.z_stack_start_pos - self._region.z_stack_step_size*slice_num
        return z_pos
    
    def _acquire_images(self):
        """
        Acquire image method for sequence acquisitions. Current sequence acquisitions iterate through channels,
        creating a separate datastore for each channel, sets summary metadata, begins sequence acquisition, and then
        writes images. This is why this general implementation is possible.
       
        I can't see a future where sequence acquisitions don't follow this pattern, but if it happens, a different
        implementation will have to be written.
        """
        for channel in self._region.z_stack_channel_list:
            self._init_hardware_for_channel(channel, self._adv_settings.z_stack_exposure)
            attempt_num = 0
            while attempt_num < ImagingSequence.ATTEMPT_LIMIT:
                self._abort_check()
                yield f"Acquiring {channel} {self._get_name()}"
                pycro.set_channel(channel)
                self._create_datastore_with_summary(channel)
                self._initialize_z_stack()
                self._start_sequence_acquisition(self._region.z_stack_num_frames)
                #num_frames*step_size is the scan distance in um; stage_speed is in um/s,
                #so their quotient is already in seconds (no extra unit factor).
                expected_duration_s = (
                    self._region.z_stack_num_frames * self._region.z_stack_step_size
                    / self._adv_settings.z_stack_stage_speed
                )
                t_start = time.monotonic()
                Stage.scan_start(self._adv_settings.z_stack_stage_speed)
                try:
                    for update_message in self._wait_for_sequence_images():
                        yield update_message
                except exceptions.CameraTimeoutException:
                    acq_record.report("camera_timeout", f"{self._get_name()} {channel}, attempt {attempt_num + 1}")
                    #upon camera timeout exception, reattempts until attempt_num == attempt limit
                    self._camera_timeout_response()
                    attempt_num += 1
                    if attempt_num < ImagingSequence.ATTEMPT_LIMIT:
                        #deletes images, unless it's the final attempt
                        self._close_and_delete_files()
                else:
                    elapsed = time.monotonic() - t_start
                    if elapsed < 0.5 * expected_duration_s:
                        self._close_and_move_files()
                        raise exceptions.HardwareException(
                            f'Z-stack completed in {elapsed:.2f}s, expected {expected_duration_s:.2f}s. '
                            'Camera trigger timing is broken - aborting to prevent corrupting more timepoints.'
                        )
                    self._close_and_move_files()
                    #breaks upon success
                    break

    def _initialize_z_stack(self):
        # Always re-apply PLC z-stack config. The previous outer guard skipped this
        # when all regions shared a step size, allowing perturbed PLC state to persist
        # across the entire timeseries. (Oct 2026: the remaining condition, which skipped this on
        # Klamath in DSLM mode, was also removed. Dual-camera snaps/videos and camera-timeout recovery
        # leave the PLC pulsing continuously, which would trigger the camera independently of the stage.)
        Plc.set_for_z_stack(self._region.z_stack_step_size, self._adv_settings.z_stack_stage_speed)
        Stage.set_z_position(self._region.z_stack_start_pos)
        Stage.initialize_scan(self._region.z_stack_start_pos, self._region.z_stack_end_pos)


class SpectralZStack(ZStack):
    """
    Note that this implements SnapAcquisition, which implements ImagingSequence,
    which means _pre_acquire_hardware_init() is required to be implemented.
    """
    def _pre_acquisition_hardware_init(self, exposure):
        Camera.set_exposure(exposure)
        if Galvo and Galvo.settings.is_lsrm:
            framerate = general_functions.exposure_to_frequency(exposure)
            Galvo.settings.lsrm_framerate = min(framerate, Camera.LSRM_MAX_FRAMERATE)
            Galvo.set_lsrm_mode()
            Plc.set_continuous_pulses(framerate)
            Camera.set_lsrm_mode(Galvo.settings.lsrm_ili, Galvo.settings.lsrm_num_lines)
        else:
            Camera.set_burst_mode()

    def _set_summary_metadata(self, channel):
        summary_builder = pycro.SummaryMetadataBuilder().channel_list(channel)
        summary_builder = summary_builder.z(self._region.z_stack_num_frames).step(self._region.z_stack_step_size)
        self._set_summary_metadata_all(summary_builder.build())

    def _pop_image_with_metadata(self, frame_num: int, channel_num: int = 0, image = None):
        image = pycro.pop_next_image() if image is None else image
        coords = pycro.ImageCoordsBuilder().c(channel_num).z(frame_num).build()
        meta = pycro.ImageMetadataBuilder(image).x(self._region.x_pos).y(self._region.y_pos).z(
            self._calculate_z_pos(frame_num)).build()
        return image.copy_with(coords, meta)

    def _acquire_images(self):
        self._pre_acquisition_hardware_init(self._adv_settings.z_stack_exposure)
        yield f"Acquiring {self._get_name()}"
        self._create_datastore_with_summary(self._region.z_stack_channel_list)
        slice_num = 0
        while slice_num < self._region.z_stack_num_frames:
            self._abort_check()
            Stage.set_z_position(self._calculate_z_pos(slice_num))
            for channel_num, channel in enumerate(self._region.z_stack_channel_list):
                self._abort_check()
                pycro.set_channel(channel)
                self._snap_image(slice_num, channel_num)
            slice_num += 1
        self._close_and_move_files()


class DeconZStack(ZStack):
    #number of different focal planes to use in taking decon images (should be odd!)
    _DECON_NUM = 3

    def _pre_acquisition_hardware_init(self, exposure):
        Camera.set_exposure(exposure)
        if microscope == MicroscopeConfig.KLAMATH or microscope == MicroscopeConfig.HTLS:
            if self._adv_settings.edge_trigger_enabled or self._region.z_stack_step_size > 1:
                Camera.set_edge_trigger_mode()
            else:
                Camera.set_sync_readout_mode()
        elif microscope == MicroscopeConfig.WILLAMETTE:
            if Camera == LS_Pycro_App.hardware.camera.Pco:
                Camera.set_ext_trig_mode()
            elif self._adv_settings.edge_trigger_enabled or self._region.z_stack_step_size > 1:
                Camera.set_edge_trigger_mode()
            else:
                Camera.set_sync_readout_mode()

    def _set_summary_metadata(self, channel):
        summary_builder = pycro.SummaryMetadataBuilder().z(self._region.z_stack_num_frames).t(DeconZStack._DECON_NUM).step(
            self._region.z_stack_step_size)
        summary_builder = summary_builder.channel_list(channel).step(self._region.z_stack_step_size)
        self._datastore.set_summary_metadata(summary_builder.build())

    def _pop_image_with_metadata(self, frame_num: int, channel_num: int = 0, image = None):
        image = pycro.pop_next_image() if image is None else image
        coords = pycro.ImageCoordsBuilder().t(frame_num%DeconZStack._DECON_NUM).z(int(np.floor(frame_num/DeconZStack._DECON_NUM))).build()
        meta = pycro.ImageMetadataBuilder(image).x(self._region.x_pos).y(self._region.y_pos).z(
            self._calculate_z_pos(int(np.floor(frame_num/DeconZStack._DECON_NUM)))).build()
        return image.copy_with(coords, meta)
        
    def _calculate_z_pos(self, slice_num: int):
        if self._region.z_stack_start_pos <= self._region.z_stack_end_pos:
            z_pos = self._region.z_stack_start_pos + self._region.z_stack_step_size*slice_num
        else:
            z_pos = self._region.z_stack_start_pos - self._region.z_stack_step_size*slice_num
        return z_pos
    
    def _acquire_images(self):
        """
        Acquire image method for sequence acquisitions. Current sequence acquisitions iterate through channels,
        creating a separate datastore for each channel, sets summary metadata, begins sequence acquisition, and then
        writes images. This is why this general implementation is possible.
       
        I can't see a future where sequence acquisitions don't follow this pattern, but if it happens, a different
        implementation will have to be written.
        """
        self._pre_acquisition_hardware_init(self._adv_settings.z_stack_exposure)
        for channel in self._region.z_stack_channel_list:
            attempt_num = 1
            while attempt_num < ImagingSequence.ATTEMPT_LIMIT:
                self._abort_check()
                yield f"Acquiring {channel} {self._get_name()}"
                pycro.set_channel(channel)
                self._create_datastore_with_summary(channel)
                self._initialize_z_stack()
                set_focus = Galvo.settings.focus
                Galvo.settings.focus -= Galvo.DECON_MODE_SHIFT
                Galvo.set_dslm_mode()
                self._start_sequence_acquisition(self._region.z_stack_num_frames*DeconZStack._DECON_NUM)
                Stage.scan_start(int(self._adv_settings.z_stack_stage_speed/DeconZStack._DECON_NUM))
                try:
                    for update_message in self._wait_for_sequence_images():
                        yield update_message
                except exceptions.CameraTimeoutException:
                    #upon camera timeout exception, reattempts until attempt_num == attempt limit
                    self._camera_timeout_response()
                    attempt_num += 1
                    if attempt_num < ImagingSequence.ATTEMPT_LIMIT:
                        self._datastore.close()
                        #deletes images, unless it's the final attempt
                        shutil.rmtree(self._acq_directory.get_directory())
                else:
                    self._datastore.close_and_move_files()
                    #breaks upon success
                    break
                finally:
                    Galvo.settings.focus = set_focus

    def _initialize_z_stack(self):
        Plc.set_for_z_stack(self._region.z_stack_step_size,  self._adv_settings.z_stack_stage_speed)
        Stage.set_z_position(self._region.z_stack_start_pos)
        Stage.initialize_scan(self._region.z_stack_start_pos, self._region.z_stack_end_pos)

    def _wait_for_sequence_images(self):
        """
        Image saving loop. This is a more advanced implementation of an example burst acquisition script on
        the Micro-Manager website.

        current_frame keeps track of current frame/slice for metadata
       
        time_no_image is the time without the core receiving an image. If this exceeds the CAMERA_TIMEOUT_MS constant,
        the current acquisition will end and the camera_timeout_response() method will be called.

        is_saving is set to True when sequence acquisition is over but there are still images in the buffer
        """
        current_frame = 0
        time_no_image = 0
        is_saving = False
        start_focus = Galvo.settings.focus
        while core.get_remaining_image_count() > 0 or core.is_sequence_running():
            if core.get_remaining_image_count() > 0:
                Galvo.settings.focus = start_focus + ((current_frame + 1) % DeconZStack._DECON_NUM)*Galvo.DECON_MODE_SHIFT
                Galvo.set_dslm_mode()
                self._abort_check()
                image = self._pop_image_with_metadata(frame_num=current_frame)
                self._datastore.put_image(image)
                current_frame += 1
                time_no_image = 0
                if not (core.is_sequence_running() or is_saving):
                    yield f"Saving {self._get_name()}"
                    is_saving = True
            elif time_no_image >= ImagingSequence.CAMERA_TIMEOUT_MS:
                raise exceptions.CameraTimeoutException
            else:
                wait_for_image_ms = 1
                core.sleep(wait_for_image_ms)
                time_no_image += wait_for_image_ms
