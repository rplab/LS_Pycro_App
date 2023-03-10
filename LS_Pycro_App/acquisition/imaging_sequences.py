"""
This module holds all the Micro-Manager image scripts. All of these are essentially adapted scripts
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
from hardware import camera, plc, stage
from models.acquisition.acq_settings import AcqSettings, Region
from models.acquisition.acq_directory import AcqDirectory
from utils import dir_functions, exceptions, pycro
from utils.pycro import core

class ImageAcquisition(ABC):
    """
    Image acquisition base class. Note that this class is expected to be inherited by a second
    abstract class, which is then inherited by aa class that includes all implementation.

    Currently, all image acquisitions fall under the following two categories:

    1. snap acquisition: All images are acquired via "snapping" an image with the camera via camera.snap_image().
    Taking images is software-controlled.

    2. sequence acquisition: All images are acquired via the Core's sequence_acquisition interface. Taking images is
    hardware-controlled, either via the camera's internal trigger or an external trigger.
    """
    @abstractmethod
    def _pre_acquire_hardware_init(self):
        """
        Sets hardware to imaging mode.
        """
        pass

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
    def _acquire_images(self, channels: str | list):
        """
        creates datastore, acquires all images in sequence, places them into the datastore, then closes datastore.
        """
        pass
    
    @abstractmethod
    def run(self):
        """
        calls set_imaging_mode() to initialize hardware and calls _acquire_images() to start image sequence.
        """
        pass
    
    def __init__(self, region: Region, acq_settings: AcqSettings, abort_flag: exceptions.AbortFlag, acq_directory: AcqDirectory):
        self._region = region
        self._acq_settings = acq_settings
        self._adv_settings = acq_settings.adv_settings
        self._abort_flag = abort_flag
        self._acq_directory = acq_directory

    def _get_name(self):
        return self.__class__.__name__.lower()

    def _create_datastore_with_summary(self, channels: str | list):
        self._acq_directory.set_acq_type(f"{self._get_name()}/{channels}".replace(",",""))
        self._datastore = pycro.multipage_datastore(self._acq_directory.get_directory())
        self._set_summary_metadata(channels)

    def close_datastore(self):
        # supress attribute error in case datastore doesn't exist
        with contextlib.suppress(AttributeError):
            self._datastore.close()
            dir_functions.move_files_to_parent(self._acq_directory.get_directory())

    def _abort_check(self):
        if self._abort_flag.abort:
            self.close_datastore()
            raise exceptions.AbortAcquisitionException

    def _set_channel(self, channel: str):
        core.set_config(core.get_channel_group(), channel)


class SequenceAcquisition(ImageAcquisition, ABC):
    """
    Image acquisition that relies on sequence acquisition implementation in Micro-Manager. In addition to
    ImageAcquisition abstract methods, also requires the _begin_sequence_acquisition() method to be implemented,
    which should initialize hardware not included in setting the imaging mode as well as start the acquisition
    itself.

    Note that that this is essentially an intermediate abstract class. Its entire purpose is to be inherited.
    """
    SINGLE_SAVE_IMAGE_LIMIT = 10000
    WAIT_FOR_IMAGE_DELAY_MS = 1
    CAMERA_TIMEOUT_MS = 2000

    @abstractmethod
    def _begin_sequence_acquisition(self):
        pass

    def _camera_timeout_response(self):
        """
        Sequence acquisitions are prone to camera timeouts if the core doesn't receive enough images. Unfortunately,
        if this happens, MM will just freeze up, and so custom implementation is required to get through a camera
        timeout.
        """
        # PLC is set to continuously pulse because when camera freezes in external trigger mode, it sometimes
        # won't allow you to set its properties without an external trigger, so this provides a trigger.
        plc.set_plc_for_continuous_lsrm(20)
        core.stop_sequence_acquisition()
        core.clear_circular_buffer()
        self.close_datastore()
        raise exceptions.CameraTimeoutException

    def _acquire_images(self, channels: list):
        """
        Acquire image method for sequence acquisitions. Current sequence acquisitions iterate through channels,
        creating a separate datastore for each channel, sets summary metadata, begins sequence acquisition, and then
        writes images. This is why this general implementation is possible.
       
        I can't see a future where sequence acquisitions don't follow this pattern, but if it happens, a different
        implementation will have to be written.
        """
        for channel in channels:
            self._abort_check()

            yield f"Acquiring {channel} {self._get_name()}"
            self._set_channel(channel)
            self._create_datastore_with_summary(channel)
            self._begin_sequence_acquisition()
            for update_message in self._wait_for_images():
                yield update_message

            self.close_datastore()

    def _wait_for_images(self):
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
                core.sleep(self.WAIT_FOR_IMAGE_DELAY_MS)
                time_no_image += self.WAIT_FOR_IMAGE_DELAY_MS


class SnapAcquisition(ImageAcquisition, ABC):
    """
    Abstract region acquisition class for acquisitions that take single, snap images instead of continuous sequence
    acquisitions.  Classes that inherit this abstract class should contain all implementation
    of image acquisition that occurs after the stage is moved to the position specified by x_pos, y_pos, z_pos in
    Region instance. This includes setting the imaging mode (the hardware settings that are specific to a certain
    acquisition), summary and image metadata, and acquiring/saving images.
    """
    def _snap_image(self, frame_num: int, channel_num: int = 0):
        """
        snaps a single image and puts it in datastore
        """
        camera.snap_image()
        image = self._pop_image_with_metadata(frame_num)
        self._datastore.put_image(image)


class Snap(SnapAcquisition):
    """
    Simple snap acquisition. Takes a single image with each channel.

    Note that this implements SnapAcquisition, which implements ImagingSequence,
    which means _pre_acquire_hardware_init() is required to be implemented.
    """
    def _set_summary_metadata(self, channel):
        summary = pycro.summary_metadata_builder().channel_list(channel).build()
        self._datastore.set_summary_metadata(summary)

    def _pop_image_with_metadata(self, frame_num: int, channel_num: int = 0):
        image = pycro.pop_next_image()
        coords = pycro.image_coords_builder().t(frame_num).build()
        meta = pycro.image_metadata_builder(image).x(self._region.x_pos).y(
            self._region.y_pos).z(self._region.z_pos).build()
        return image.copy_with(coords, meta)

    def _acquire_images(self, channels):
        self._abort_check()
        for channel_num, channel in enumerate(channels):
            self._abort_check()

            yield f"Acquiring {channel} {self._get_name()}"
            self._create_datastore_with_summary(channel)
            self._set_channel(channel)
            self._snap_image(0)
            
            self.close_datastore()
    
    def run(self):
        self._pre_acquire_hardware_init()
        for update_message in self._acquire_images(self._region.snap_channel_list):
            yield update_message


class Video(SequenceAcquisition):
    """

    Note that this implements SnapAcquisition, which implements ImagingSequence,
    which means _pre_acquire_hardware_init() is required to be implemented.
    """
    def _set_summary_metadata(self, channel):
        summary_builder = pycro.summary_metadata_builder().t(self._region.video_num_frames)
        summary_builder = summary_builder.channel_list(channel)
        summary_builder = summary_builder.interval_ms(self._region.video_exposure)
        self._datastore.set_summary_metadata(summary_builder.build())

    def _pop_image_with_metadata(self, frame_num: int, channel_num: int = 0):
        image = pycro.pop_next_image()
        coords = pycro.image_coords_builder().t(frame_num).build()
        meta = pycro.image_metadata_builder(image).x(self._region.x_pos).y(
            self._region.y_pos).z(self._region.z_pos).build()
        return image.copy_with(coords, meta)

    def _begin_sequence_acquisition(self):
        camera.start_sequence_acquisition(self._region.video_num_frames)

    def run(self):
        self._pre_acquire_hardware_init()
        for update_message in self._acquire_images(self._region.video_channel_list):
            yield update_message


class VideoSingleSave(Video):
    """
    """
    def _create_datastore_with_summary(self, channels: str | list):
        self._acq_directory.set_acq_type(f"{self._get_name()}/{channels}".replace(",",""))
        self._datastore = pycro.ram_datastore()
        self._set_summary_metadata(channels)

    def _acquire_images(self, channels: list):
        self._create_datastore_with_summary(channels)

        for channel_num, channel in enumerate(channels):
            self._abort_check()

            yield f"Acquiring {channel} {self._get_name()}"
            self._set_channel(channel)
            self._begin_sequence_acquisition()
            for update_message in self._wait_for_images(channel_num):
                yield update_message

        self._datastore.save(self._acq_directory.get_directory())
        self.close_datastore()


class SpectralVideo(Video, SnapAcquisition):
    """

    Note that this implements SnapAcquisition, which implements ImagingSequence,
    which means _pre_acquire_hardware_init() is required to be implemented.
    """
    def _set_summary_metadata(self, channel):
        summary_builder = pycro.summary_metadata_builder().channel_list(channel)
        summary_builder = summary_builder.t(self._region.video_num_frames)
        summary_builder = summary_builder.interval_ms(self._region.video_exposure)
        self._datastore.set_summary_metadata(summary_builder.build())
    
    def _pop_image_with_metadata(self, frame_num: int, channel_num: int = 0):
        image = pycro.pop_next_image()
        coords = pycro.image_coords_builder().c(channel_num).t(frame_num).build()
        meta = pycro.image_metadata_builder(image).x(self._region.x_pos).y(
            self._region.y_pos).z(self._region.z_pos).build()
        return image.copy_with(coords, meta)

    def _acquire_images(self, channels):
        yield f"Acquiring {self._get_name()}"
        self._create_datastore_with_summary(channels)

        current_frame = 0
        while current_frame < self._region.video_num_frames:
            for channel_num, channel in enumerate(channels):
                self._abort_check()
                self._set_channel(channel)
                self._snap_image(current_frame, channel_num)
            current_frame += 1

        self.close_datastore()


class ZStack(SequenceAcquisition):
    """

    Note that this implements SnapAcquisition, which implements ImagingSequence,
    which means _pre_acquire_hardware_init() is required to be implemented.
    """
    def _set_summary_metadata(self, channel):
        summary_builder = pycro.summary_metadata_builder().z(self._region.get_z_stack_num_frames()).step(
            self._region.z_stack_step_size)
        summary_builder = summary_builder.channel_list(channel).step(self._region.z_stack_step_size)
        self._datastore.set_summary_metadata(summary_builder.build())

    def _pop_image_with_metadata(self, frame_num: int, channel_num: int = 0):
        image = pycro.pop_next_image()
        coords = pycro.image_coords_builder().z(frame_num).build()
        meta = pycro.image_metadata_builder(image).x(self._region.x_pos).y(self._region.y_pos).z(
            self._calculate_z_pos(frame_num)).build()
        return image.copy_with(coords, meta)
    
    def _begin_sequence_acquisition(self):
        self._initialize_z_stack()
        camera.start_sequence_acquisition(self._region.get_z_stack_num_frames())
        stage.scan_start(self._adv_settings.z_stack_stage_speed)

    def _calculate_z_pos(self, slice_num: int):
        if self._region.z_stack_start_pos <= self._region.z_stack_end_pos:
            z_pos = self._region.z_stack_start_pos + self._region.z_stack_step_size*slice_num
        else:
            z_pos = self._region.z_stack_start_pos - self._region.z_stack_step_size*slice_num
        return z_pos

    def _initialize_z_stack(self):
        if not self._acq_settings._is_step_size_same():
            step_size = self._region.z_stack_step_size
            stage_speed = self._adv_settings.z_stack_stage_speed
            plc.set_plc_for_z_stack(step_size, stage_speed)
        stage.set_z_position(self._region.z_stack_start_pos)
        stage.initialize_scan(self._region.z_stack_start_pos, self._region.z_stack_end_pos)

    def run(self):
        self._pre_acquire_hardware_init()
        for update_message in self._acquire_images(self._region.z_stack_channel_list):
            yield update_message


class SpectralZStack(ZStack, SnapAcquisition):
    """
    
    Note that this implements SnapAcquisition, which implements ImagingSequence,
    which means _pre_acquire_hardware_init() is required to be implemented.
    """
    def _set_summary_metadata(self, channel):
        summary_builder = pycro.summary_metadata_builder().channel_list(channel)
        summary_builder = summary_builder.z(self._region.get_z_stack_num_frames()).step(self._region.z_stack_step_size)
        self._datastore.set_summary_metadata(summary_builder.build())

    def _pop_image_with_metadata(self, frame_num: int, channel_num: int = 0):
        image = pycro.pop_next_image()
        coords = pycro.image_coords_builder().c(channel_num).z(frame_num).build()
        meta = pycro.image_metadata_builder(image).x(self._region.x_pos).y(self._region.y_pos).z(
            self._calculate_z_pos(frame_num)).build()
        return image.copy_with(coords, meta)

    def _acquire_images(self, channels):
        yield f"Acquiring {self._get_name()}"
        self._create_datastore_with_summary(channels)
        
        slice_num = 0
        while slice_num < self._region.get_z_stack_num_frames():
            self._abort_check()
            stage.set_z_position(self._calculate_z_pos(slice_num))
            for channel_num, channel in enumerate(channels):
                self._abort_check()
                self._set_channel(channel)
                self._snap_image(slice_num, channel_num)
            slice_num += 1
       
        self.close_datastore()
