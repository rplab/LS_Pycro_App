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

import contextlib
from abc import ABC, abstractmethod

import LS_Pycro_App.hardware.camera
from LS_Pycro_App.models.acq_settings import AcqSettings, Region
from LS_Pycro_App.models.acq_directory import AcqDirectory
from LS_Pycro_App.hardware import Camera, Plc, Stage, Galvo
from LS_Pycro_App.controllers.select_controller import microscope, MicroscopeConfig
from LS_Pycro_App.utils import dir_functions, exceptions, pycro, general_functions
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
    
    def __init__(self, region: Region, acq_settings: AcqSettings, abort_flag: exceptions.AbortFlag, acq_directory: AcqDirectory):
        self._region = region
        self._acq_settings = acq_settings
        self._adv_settings = acq_settings.adv_settings
        self._abort_flag = abort_flag
        self._acq_directory = acq_directory

    def close_datastore(self):
        # supress attribute error in case datastore doesn't exist
        with contextlib.suppress(AttributeError):
            self._datastore.close()
            #MM creates a folder with the smame name as the filename, which I found redundant, so the files are moved
            #to the parent folder and that folder is deleted.
            dir_functions.move_files_to_parent(self._acq_directory.get_directory())

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
            self.close_datastore()
            raise exceptions.AbortAcquisitionException
        
    def _pre_acquisition_hardware_init(self, exposure):
        Camera.set_exposure(exposure)
        if Camera == LS_Pycro_App.hardware.camera.Hamamatsu:
            if self._adv_settings.lsrm_enabled and Galvo:
                framerate = general_functions.exposure_to_frequency(exposure)
                Galvo.settings.lsrm_framerate = min(framerate, Camera.LSRM_MAX_FRAMERATE)
                Galvo.set_lsrm_mode()
                Plc.set_continuous_pulses(framerate)
                Camera.set_lsrm_mode(Galvo.settings.lsrm_ili, Galvo.settings.lsrm_num_lines)
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
                time_no_image = 0
                if not (core.is_sequence_running() or is_saving):
                    yield f"Saving {self._get_name()}"
                    is_saving = True
            elif time_no_image >= self.CAMERA_TIMEOUT_MS:
                self._camera_timeout_response()
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
        Plc.set_continuous_pulses(20)
        core.stop_sequence_acquisition()
        core.clear_circular_buffer()
        self.close_datastore()
        raise exceptions.CameraTimeoutException


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
            self.close_datastore()


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
        self._pre_acquisition_hardware_init(self._region.video_exposure)
        for channel in self._region.video_channel_list:
            self._abort_check()
            yield f"Acquiring {channel} {self._get_name()}"
            pycro.set_channel(channel)
            self._create_datastore_with_summary(channel)
            self._start_sequence_acquisition(self._region.video_num_frames)
            for update_message in self._wait_for_sequence_images():
                yield update_message
            self.close_datastore()


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
        self.close_datastore()


class ZStack(ImagingSequence):
    """
    Z-Stack works by setting camera to external trigger mode, setting the stage to scan, and then
    having the PLC trigger the camera at specific intervals to acquire images. Because of this,
    Z-Stack requires the PLC and stage scan to be initialized before acquisition begins.
    Then, the sequence acquisition is started, the stage starts scanning, and images are collected.
    """
    def _pre_acquisition_hardware_init(self, exposure):
        Camera.set_exposure(exposure)
        if microscope == MicroscopeConfig.KLAMATH:
            if self._adv_settings.lsrm_enabled and Galvo:
                framerate = general_functions.exposure_to_frequency(exposure)
                Galvo.settings.lsrm_framerate = min(framerate, Camera.LSRM_MAX_FRAMERATE)
                Galvo.set_lsrm_mode()
                Plc.set_for_z_stack(self._region.z_stack_step_size, self._adv_settings.z_stack_stage_speed)
                Camera.set_lsrm_mode(Galvo.settings.lsrm_ili, Galvo.settings.lsrm_num_lines)
            elif self._adv_settings.edge_trigger_enabled or self._region.z_stack_step_size > 1:
                Camera.set_edge_trigger_mode()
            else:
                Camera.set_sync_readout_mode()
        elif microscope == MicroscopeConfig.WILLAMETTE:
            Camera.set_ext_trig_mode()

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
            self._abort_check()
            yield f"Acquiring {channel} {self._get_name()}"
            pycro.set_channel(channel)
            self._create_datastore_with_summary(channel)
            self._initialize_z_stack()
            self._start_sequence_acquisition(self._region.z_stack_num_frames)
            Stage.scan_start(self._adv_settings.z_stack_stage_speed)
            for update_message in self._wait_for_sequence_images():
                yield update_message
            self.close_datastore()

    def _initialize_z_stack(self):
        if not self._acq_settings.is_step_size_same():
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
        if Camera == LS_Pycro_App.hardware.camera.Hamamatsu:
            if self._adv_settings.lsrm_enabled and Galvo:
                framerate = general_functions.exposure_to_frequency(exposure)
                Galvo.settings.lsrm_framerate = min(framerate, Camera.LSRM_MAX_FRAMERATE)
                Galvo.set_lsrm_mode()
                Plc.set_continuous_pulses(framerate)
                Camera.set_lsrm_mode(Galvo.settings.lsrm_ili, Galvo.settings.lsrm_num_lines)
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
        self.close_datastore()
