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

import shutil
from abc import ABC, abstractmethod

import numpy as np

import LS_Pycro_App.hardware.camera
from LS_Pycro_App.models.acq_settings import AcqSettings, Region
from LS_Pycro_App.models.acq_directory import AcqDirectory
from LS_Pycro_App.hardware import Camera, Plc, Stage, Galvo, multi_device
from LS_Pycro_App.controllers.select_controller import microscope, MicroscopeConfig
from LS_Pycro_App.utils import constants, exceptions, pycro, general_functions
from LS_Pycro_App.utils.pycro import core


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
    def _pop_image_with_metadata(self, frame_num: int, channel_num: int = 0):
        """
        pops the next image from the MM circular buffer, grabs its metadata, updates its metadata, 
        and then returns image with the updated metadata.

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

    def run(self):
        for update_message in self._acquire_images():
            yield update_message

    def _get_name(self):
        return self.__class__.__name__.lower()

    def _create_datastore_with_summary(self, channels: str | list):
        self._acq_directory.set_acq_type(f"{self._get_name()}/{channels}".replace(",",""))
        self._datastore = pycro.MultipageDatastore(self._acq_directory.get_directory())
        self._set_summary_metadata(channels)

    def _abort_check(self):
        if self._abort_flag.abort:
            self._datastore.close_and_move_files()
            raise exceptions.AbortAcquisitionException
        
    def _pre_acquisition_hardware_init(self, exposure):
        # No matter what, set exposure time
        Camera.set_exposure(exposure)
        if Camera == LS_Pycro_App.hardware.camera.Hamamatsu:
            # 
            if Galvo:
                if Galvo.settings.is_lsrm:
                    multi_device.set_lsrm_from_exposure(exposure)
                else:
                    Camera.set_burst_mode()
        elif Camera == LS_Pycro_App.hardware.camera.Pco:
            Camera.set_burst_mode()

    def _snap_image(self, frame_num: int, channel_num: int = 0):
        """
        snaps a single image and puts it in datastore
        """
        Camera.snap_image()
        image = self._pop_image_with_metadata(frame_num, channel_num)
        self._datastore.put_image(image)

    def _start_sequence_acquisition(self, num_frames: int):
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
        time_no_image = 0
        is_saving = False
        while core.get_remaining_image_count() > 0 or core.is_sequence_running():
            if core.get_remaining_image_count() > 0:
                self._abort_check()
                image = self._pop_image_with_metadata(frame_num=current_frame)
                self._datastore.put_image(image)
                current_frame += 1
                yield f"Acquired {current_frame + 1} / {self._region.z_stack_num_frames} frames"
                time_no_image = 0
                if not (core.is_sequence_running() or is_saving):
                    yield f"Saving {self._get_name()}"
                    is_saving = True
            elif time_no_image >= ImagingSequence.CAMERA_TIMEOUT_MS:
                yield f"CameraTimeoutException raised during {self.__class__.__name__} sequence after no image for {round(time_no_image/10**3, 3)} seconds"
                raise exceptions.CameraTimeoutException
            else:
                core.sleep(self.WAIT_FOR_IMAGE_MS)
                time_no_image += self.WAIT_FOR_IMAGE_MS

    def _camera_timeout_response(self):
        """
        Sequence acquisitions are prone to camera timeouts if the core doesn't receive enough images. Unfortunately,
        if this happens, MM will just freeze up, and so custom implementation is required to get through a camera
        timeout.
        """
        #Camera times out because it's expecting a certain number of pulses, and it if it doesn't receive them,
        #it freezes up. Plc is set to pulse so it unfreezes the camera, allowing us to stop the sequence acquisition.
        Plc.set_to_continuous_pulse_mode(constants.CAMERA_RECOVERY_PULSE_INTERVAL_MS)
        core.stop_sequence_acquisition()
        core.clear_circular_buffer()
        self._datastore.close()


class Snap(ImagingSequence):
    """
    Simple snap acquisition. Takes a single image with each channel.
    """
    def _pop_image_with_metadata(self, frame_num: int, channel_num: int = 0):
        image = pycro.pop_next_image()
        coords = pycro.ImageCoordsBuilder().t(frame_num).build()
        meta = pycro.ImageMetadataBuilder(image).x(self._region.x_pos).y(
            self._region.y_pos).z(self._region.z_pos).build()
        return image.copy_with(coords, meta)
    
    def _set_summary_metadata(self, channel):
        summary = pycro.SummaryMetadataBuilder().channel_list(channel).build()
        self._datastore.set_summary_metadata(summary)

    def _acquire_images(self):
        self._pre_acquisition_hardware_init(self._region.snap_exposure)
        self._abort_check()
        for channel in self._region.snap_channel_list:
            self._abort_check()
            yield f"Acquiring {channel} {self._get_name()}"
            self._create_datastore_with_summary(channel)
            pycro.set_channel(channel)
            self._snap_image(0)
            self._datastore.close_and_move_files()


class Video(ImagingSequence):
    """
    Standard video. Takes a continuous video with region.video_num_frames with each channel provided.
    """
    def _set_summary_metadata(self, channel):
        summary_builder = pycro.SummaryMetadataBuilder().t(self._region.video_num_frames)
        summary_builder = summary_builder.channel_list(channel)
        summary_builder = summary_builder.interval_ms(self._region.video_exposure)
        self._datastore.set_summary_metadata(summary_builder.build())

    def _pop_image_with_metadata(self, frame_num: int, channel_num: int = 0):
        image = pycro.pop_next_image()
        coords = pycro.ImageCoordsBuilder().t(frame_num).build()
        meta = pycro.ImageMetadataBuilder(image).x(self._region.x_pos).y(
            self._region.y_pos).z(self._region.z_pos).build()
        return image.copy_with(coords, meta)

    def _acquire_images(self):
        """
        Acquire image method for sequence acquisitions. Current sequence acquisitions iterate through channels,
        creating a separate datastore for each channel, sets summary metadata, begins sequence acquisition, and then
        writes images. This is why this general implementation is possible.
       
        I can't see a future where sequence acquisitions don't follow this pattern, but if it happens, a different
        implementation will have to be written.
        """
        self._pre_acquisition_hardware_init(self._adv_settings.z_stack_exposure)
        for channel in self._region.video_channel_list:
            attempt_num = 0
            while attempt_num < ImagingSequence.ATTEMPT_LIMIT:
                self._abort_check()
                yield f"Acquiring {channel} {self._get_name()}"
                pycro.set_channel(channel)
                self._create_datastore_with_summary(channel)
                self._start_sequence_acquisition(self._region.video_num_frames)
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


class SpectralVideo(Video):
    """
    Video that switches between channels every image. Video finishes when there
    are region.video_num_images images of each channel.
    """
    def _set_summary_metadata(self, channel):
        summary_builder = pycro.SummaryMetadataBuilder().channel_list(channel)
        summary_builder = summary_builder.t(self._region.video_num_frames)
        summary_builder = summary_builder.interval_ms(self._region.video_exposure)
        self._datastore.set_summary_metadata(summary_builder.build())

    def _pop_image_with_metadata(self, frame_num: int, channel_num: int = 0):
        image = pycro.pop_next_image()
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
        self._datastore.close_and_move_files()


class ZStack(ImagingSequence):
    """
    Z-Stack works by setting camera to external trigger mode, setting the stage to scan, and then
    having the PLC trigger the camera at specific intervals to acquire images. Because of this,
    Z-Stack requires the PLC and stage scan to be initialized before acquisition begins.
    Then, the sequence acquisition is started, the stage starts scanning, and images are collected.
    """
    def _pre_acquisition_hardware_init(self, exposure):
        Camera.set_exposure(exposure)
        if Camera == LS_Pycro_App.hardware.camera.Hamamatsu:
            if Galvo and Galvo.settings.is_lsrm:
                interval_ms = self._region.z_stack_step_size/self._adv_settings.z_stack_stage_speed*constants.S_TO_MS
                multi_device.set_triggered_lsrm(exposure, interval_ms)
            elif self._adv_settings.edge_trigger_enabled or self._region.z_stack_step_size > 1:
                Camera.set_edge_trigger_mode()
            else:
                Camera.set_sync_readout_mode()
        elif microscope == MicroscopeConfig.WILLAMETTE:
            Camera.set_ext_trig_mode()

    def _camera_timeout_response(self):
        #calls default camera reset function from super class
        super()._camera_timeout_response()
        interval_ms = self._region.z_stack_step_size/self._adv_settings.z_stack_stage_speed*constants.S_TO_MS
        Plc.set_to_external_trigger_mode(interval_ms)

    def _set_summary_metadata(self, channel):
        summary_builder = pycro.SummaryMetadataBuilder().z(self._region.z_stack_num_frames).step(
            self._region.z_stack_step_size)
        summary_builder = summary_builder.channel_list(channel).step(self._region.z_stack_step_size)
        self._datastore.set_summary_metadata(summary_builder.build())

    def _pop_image_with_metadata(self, frame_num: int, channel_num: int = 0):
        image = pycro.pop_next_image()
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
        self._pre_acquisition_hardware_init(self._adv_settings.z_stack_exposure)
        for channel in self._region.z_stack_channel_list:
            attempt_num = 0
            while attempt_num < ImagingSequence.ATTEMPT_LIMIT:
                self._abort_check()
                yield f"Acquiring {channel} {self._get_name()}"
                pycro.set_channel(channel)
                self._create_datastore_with_summary(channel)
                self._initialize_z_stack()
                self._start_sequence_acquisition(self._region.z_stack_num_frames)
                Stage.scan_start(self._adv_settings.z_stack_stage_speed)
                try:
                    for update_message in self._wait_for_sequence_images():
                        yield update_message
                except exceptions.CameraTimeoutException:
                    #upon camera timeout exception, reattempts until attempt_num == attempt limit
                    self._camera_timeout_response()
                    attempt_num += 1
                    if attempt_num < ImagingSequence.ATTEMPT_LIMIT:
                        self._datastore.close()
                        yield f"raised CameraTimeoutException on attempt {attempt_num + 1}. Removing images and reaatempting"
                        #deletes images, unless it's the final attempt
                        shutil.rmtree(self._acq_directory.get_directory())
                    else:
                        yield f"Z stack failed {attempt_num + 1} attempts. Skipping to next imaging sequence."
                else:
                    self._datastore.close_and_move_files()
                    #breaks upon success
                    break

    def _initialize_z_stack(self):
        if not self._acq_settings.is_step_size_same():
            if not Galvo or (Galvo.settings.is_lsrm and (self._region.snap_enabled or self._region.video_enabled)):
                interval_ms = self._region.z_stack_step_size/self._adv_settings.z_stack_stage_speed*constants.S_TO_MS
                Plc.set_to_external_trigger_mode(interval_ms)
        Stage.set_z_position(self._region.z_stack_start_pos)
        Stage.initialize_scan(self._region.z_stack_start_pos, self._region.z_stack_end_pos)


class SpectralZStack(ZStack):
    """
    Note that this implements SnapAcquisition, which implements ImagingSequence,
    which means _pre_acquire_hardware_init() is required to be implemented.
    """
    def _pre_acquisition_hardware_init(self, exposure):
        Camera.set_exposure(exposure)
        if Camera == LS_Pycro_App.hardware.camera.Hamamatsu:
            if Galvo:
                if Galvo.settings.is_lsrm:
                    framerate = general_functions.exposure_to_frequency(exposure)
                    multi_device.set_continuous_lsrm(framerate)
                else:
                    Camera.set_burst_mode()
        elif Camera == LS_Pycro_App.hardware.camera.Pco:
            Camera.set_burst_mode()

    def _set_summary_metadata(self, channel):
        summary_builder = pycro.SummaryMetadataBuilder().channel_list(channel)
        summary_builder = summary_builder.z(self._region.z_stack_num_frames).step(self._region.z_stack_step_size)
        self._datastore.set_summary_metadata(summary_builder.build())

    def _pop_image_with_metadata(self, frame_num: int, channel_num: int = 0):
        image = pycro.pop_next_image()
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
        self._datastore.close_and_move_files()


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
            Camera.set_ext_trig_mode()

    def _set_summary_metadata(self, channel):
        summary_builder = pycro.SummaryMetadataBuilder().z(self._region.z_stack_num_frames).t(DeconZStack._DECON_NUM).step(
            self._region.z_stack_step_size)
        summary_builder = summary_builder.channel_list(channel).step(self._region.z_stack_step_size)
        self._datastore.set_summary_metadata(summary_builder.build())

    def _pop_image_with_metadata(self, frame_num: int, channel_num: int = 0):
        image = pycro.pop_next_image()
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
        if not self._acq_settings.is_step_size_same():
            interval_ms = self._region.z_stack_step_size/self._adv_settings.z_stack_stage_speed*constants.S_TO_MS
            Plc.set_to_external_trigger_mode(interval_ms)
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
