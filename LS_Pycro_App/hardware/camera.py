import logging
from abc import ABC, abstractmethod
from hardware.exceptions_handle import handle_exception
from utils.abc_attributes_wrapper import abstractattributes
from utils.pycro import studio, core


@abstractattributes
class Camera(ABC):
    #"abstract attributes" Interpreter will throw an error if the following aren't declared.
    MAX_EXPOSURE : float
    MIN_EXPOSURE : float

    @abstractmethod
    def set_burst_mode(cls):
        """
        puts camera into burst (continuous) mode.
        """
        pass
    
    _logger = logging.getLogger(__name__)
    CAM_NAME : str = core.get_camera_device()

    _WAIT_FOR_IMAGE_MS : float = 0.1
    DEFAULT_EXPOSURE : float = 20
    
    @classmethod
    @handle_exception
    def set_property(cls, property_name: str, value):
        """
        Sets given camera property name to value
        """
        core.set_property(cls.CAM_NAME, property_name, value)

    @classmethod
    @handle_exception
    def wait_for_camera(cls):
        core.wait_for_device(cls.CAM_NAME)

    @classmethod
    @handle_exception
    def start_sequence_acquisition(cls, num_frames: int):
        """
        Starts continuous sequence acquisition of number of images specified by num_frames.
        """
        #start_sequence_acquisition takes the arguments (long numImages, double intervalMs, bool stopOnOverflow)
        core.start_sequence_acquisition(num_frames, 0, True)
        cls._logger.info(f"Started sequence acquistiion of {num_frames} frames")
    
    @classmethod
    @handle_exception
    def snap_image(cls):
        """
        Snaps an image with the camera. Image is then put in circular buffer where it can be grabbed with
        utils.pycro.pop_next_image(), which will return the image as a Micro-Manager image object.
        """
        #Originally when I scripted with MM, I would just use the snap() method in the studio.acquisition class, 
        # but this doesn't work with lsrm for some reason.
        core.start_sequence_acquisition(1, 0, True)
        #waits until image is actually in buffer. 
        while not core.get_remaining_image_count():
            core.sleep(cls._WAIT_FOR_IMAGE_MS)

        cls._logger.info(f"Snapped image")

    @classmethod
    @handle_exception
    def stop_live_acquisition(cls):
        """
        Turns live mode off in Micro-Manager, stopping live acquisition.
        """
        core.wait_for_device(cls.CAM_NAME)
        studio.live().set_live_mode_on(False)
        cls._logger.info(f"Stopped live acquisition")
        