import logging
import time
from abc import ABC, abstractmethod

from LS_Pycro_App.hardware.exceptions_handle import handle_exception
from LS_Pycro_App.utils.abc_attributes_wrapper import abstractattributes
from LS_Pycro_App.utils import general_functions, constants, exceptions
from LS_Pycro_App.utils.pycro import studio, core


#Micro-Manager "Multi Camera" utility device. On Klamath it combines HamamatsuHam_DCAM and
#HamamatsuHam_DCAM2 for simultaneous dual-camera acquisition (see KLA_23April2026_CLS3.cfg).
MULTI_CAM_NAME = "MultiCamera"


def _get_default_camera_name() -> str:
    """
    Returns the label of the camera Micro-Manager is configured to use (Core-Camera).

    If the app previously exited in the middle of a dual-camera acquisition, Core-Camera may still be
    the MultiCamera device; in that case the first physical camera is returned.
    """
    name = core.get_camera_device()
    if name == MULTI_CAM_NAME:
        name = core.get_property(MULTI_CAM_NAME, "Physical Camera 1")
    return name


def select_multi_camera():
    """
    Makes the MultiCamera device Micro-Manager's active camera (dual-camera acquisitions, Klamath only).
    Must not be called while a sequence acquisition (including live mode) is running.
    """
    if core.get_camera_device() != MULTI_CAM_NAME:
        core.set_camera_device(MULTI_CAM_NAME)


@abstractattributes
class Camera(ABC):
    #"abstract attributes" Interpreter will throw an error if the following aren't declared.
    MAX_EXPOSURE : float
    MIN_EXPOSURE : float

    @abstractmethod
    def set_burst_mode(cls):
        """
        puts camera into burst (continuous) mode, using internal trigger to
        take images.
        """
        pass
    
    _logger = logging.getLogger(__name__)
    CAM_NAME : str = _get_default_camera_name()

    _WAIT_FOR_IMAGE_MS : float = 0.01
    #A snap gives up if no frame arrives within (exposure + this margin).
    SNAP_TIMEOUT_MARGIN_S : float = 2.0
    DEFAULT_EXPOSURE : float = 20

    @classmethod
    def select(cls):
        """
        Makes this camera Micro-Manager's active (Core-Camera) device, if it isn't already.

        MMCore refuses to change the camera while a sequence acquisition (which includes live mode) is
        running, even if the requested camera is the current one, so set_camera_device() is only called
        when the camera actually needs to change. Callers must make sure no sequence acquisition is running.
        """
        if core.get_camera_device() != cls.CAM_NAME:
            core.set_camera_device(cls.CAM_NAME)
            cls._logger.info(f"Active camera set to {cls.CAM_NAME}")
    
    @classmethod
    @handle_exception
    def set_property(cls, property_name: str, value):
        """
        Sets given camera MM property to value.
        """
        core.set_property(cls.CAM_NAME, property_name, value)

    @classmethod
    @handle_exception
    def set_exposure(cls, exposure: float):
        #Sets the exposure of this specific camera (by label), without changing the active camera.
        core.set_exposure(cls.CAM_NAME, exposure)
        cls._logger.info(f"{cls.CAM_NAME} exposure set to {exposure} ms")
        
    @classmethod
    @handle_exception
    def wait_for_camera(cls):
        core.wait_for_device(cls.CAM_NAME)
        cls._logger.info(f"Waiting for camera")

    @classmethod
    @handle_exception
    def start_sequence_acquisition(cls, num_frames: int):
        """
        Starts continuous sequence acquisition of number of images specified by num_frames.
        """
        cls.select()
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
        core.stop_sequence_acquisition()
        cls.select()
        exposure_ms = core.get_exposure()
        #Originally when I scripted with MM, I would just use the snap() method in the studio.acquisition class, 
        # but this doesn't work with lsrm for some reason.
        core.start_sequence_acquisition(1, 0, True)
        #Waits until image is actually in buffer, but not forever: if no frame arrives within
        #exposure + SNAP_TIMEOUT_MARGIN_S (e.g. an external trigger never arrives), the snap fails loudly
        #instead of hanging the acquisition indefinitely.
        deadline = time.monotonic() + exposure_ms*constants.MS_TO_S + cls.SNAP_TIMEOUT_MARGIN_S
        while not core.get_remaining_image_count() > 0:
            if time.monotonic() > deadline:
                core.stop_sequence_acquisition()
                raise exceptions.CameraTimeoutException(
                    f"Snap timed out: {cls.CAM_NAME} received no frame within "
                    f"{exposure_ms} ms exposure + {cls.SNAP_TIMEOUT_MARGIN_S} s")
            core.sleep(cls._WAIT_FOR_IMAGE_MS)
        core.stop_sequence_acquisition()
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

    @classmethod
    @handle_exception
    def start_live_acquisition(cls):
        """
        Turns live mode on in Micro-Manager with this camera. Safe to call when live mode is already on.
        """
        live = studio.live()
        if live.is_live_mode_on():
            if core.get_camera_device() == cls.CAM_NAME:
                cls._logger.info(f"Live mode already on")
                return
            #Live is running on a different camera (e.g. MultiCamera); stop it so the camera can be changed.
            live.set_live_mode_on(False)
        if core.is_sequence_running():
            core.stop_sequence_acquisition()
        cls.select()
        core.wait_for_device(cls.CAM_NAME)
        live.set_live_mode_on(True)
        cls._logger.info(f"Started live acquisition")
        

class Pco(Camera):
    #Can't seem to figure out what the max or min is for PCO. Isn't clear in documentation.
    MAX_EXPOSURE = 2000
    MIN_EXPOSURE = .010

    #Camera property names
    _TRIGGER_MODE_PROP = "Triggermode"
    _ACQUIRE_MODE_PROP = "Acquiremode"

    #Camera properties
    _BURST_ACQUIRE_MODE = "Internal"
    _BURST_TRIGGER_MODE = "Software"
    _Z_STACK_ACQUIRE_MODE = "External"
    _Z_STACK_TRIGGER_MODE = "External"

    @classmethod
    @handle_exception
    def set_burst_mode(cls):
        cls.wait_for_camera()
        core.stop_sequence_acquisition()
        studio.live().set_live_mode_on(False)
        cls.set_property(cls._TRIGGER_MODE_PROP, cls._BURST_TRIGGER_MODE)
        cls.set_property(cls._ACQUIRE_MODE_PROP,cls. _BURST_ACQUIRE_MODE)

    @classmethod
    @handle_exception
    def set_ext_trig_mode(cls):
        """
        Sets the camera properties for a z-stack.

        Currently, only changes the trigger mode to external and changes
        the exposure time according to the parameters z_scan+_speed and exposure.

        Parameters:

        exposure:int - Sets the exposure time for scan, unless larger than
        max exposure time

        z_stack_speed:float - Used in determining max exposure time for scan
        """
        cls.wait_for_camera()
        core.stop_sequence_acquisition()
        studio.live().set_live_mode_on(False)
        cls.set_property(cls._TRIGGER_MODE_PROP, cls._Z_STACK_TRIGGER_MODE)
        cls.set_property(cls._ACQUIRE_MODE_PROP, cls._Z_STACK_ACQUIRE_MODE)


class Hamamatsu(Camera):
    """
    This class contains methods to and properties to control our 
    Hamamatsu C11440-22CU.

    Hamamatsu manual (Download link of PDF. Check downloads.)

    https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=&ved=2ahUKEwiBw9qNsZD7AhURKn0KHcDbDWQQFnoECAsQAQ&url=https%3A%2F%2Fwiki.umontreal.ca%2Fdownload%2Fattachments%2F189567146%2FHamamatsu_Orca%2520Flash%25204.0_V2_C11440-22CU_Instruction%2520Manual.pdf%3Fversion%3D1%26modificationDate%3D1627866006000%26api%3Dv2&usg=AOvVaw3vpbp7BfjOyA9mwO81xykH
    """
    MAX_EXPOSURE = 2000
    MIN_EXPOSURE = .010
    DEFAULT_BINNING = 1
    DETECTION_BINNING = 2
    DETECTION_EXPOSURE = 10

    #Hamamatsu property names
    _SENSOR_MODE_PROP = "SENSOR MODE"
    _TRIGGER_POLARITY_PROP = "TriggerPolarity"
    _TRIGGER_SOURCE_PROP = "TRIGGER SOURCE"
    _TRIGGER_ACTIVE_PROP = "TRIGGER ACTIVE"
    _ILI_PROP = "INTERNAL LINE INTERVAL"

    #Hamamatsu properties
    _AREA_SENSOR_MODE = "AREA"
    _LSRM_SENSOR_MODE = "PROGRESSIVE"
    _NEGATIVE_POLARITY = "NEGATIVE"
    _POSITIVE_POLARITY= "POSITIVE"
    _INTERNAL_SOURCE = "INTERNAL"
    _EXTERNAL_SOURCE = "EXTERNAL"
    _EDGE_TRIGGER = "EDGE"
    _SYNC_READOUT = "SYNCREADOUT"
    READOUT_PER_ROW_S = 9.74436*10**-6
    NUM_LINES_DELAY = 9
    LSRM_MAX_FRAMERATE = 49

    @classmethod
    @handle_exception
    def set_burst_mode(cls):
        cls.stop_live_acquisition()
        cls.set_property(cls._SENSOR_MODE_PROP, cls._AREA_SENSOR_MODE)
        cls.set_property(cls._TRIGGER_POLARITY_PROP, cls._NEGATIVE_POLARITY)
        cls.set_property(cls._TRIGGER_SOURCE_PROP, cls._INTERNAL_SOURCE)
        cls.set_property(cls._TRIGGER_ACTIVE_PROP, cls._EDGE_TRIGGER)

    @classmethod
    @handle_exception
    def set_edge_trigger_mode(cls):
        """
        Puts camera into edge trigger mode. Exposure time is limited by framerate, and so exposure time passed in
        may not be the actual exposure time set. See the Hamamatsu documentation for more details.

        Currently used during z-stacks where the desired exposure time is below 1/stage_speed. 
        """
        cls.stop_live_acquisition()
        cls.set_property(cls._SENSOR_MODE_PROP, cls._AREA_SENSOR_MODE)
        cls.set_property(cls._TRIGGER_POLARITY_PROP, cls._POSITIVE_POLARITY)
        cls.set_property(cls._TRIGGER_SOURCE_PROP, cls._EXTERNAL_SOURCE)
        cls.set_property(cls._TRIGGER_ACTIVE_PROP, cls._EDGE_TRIGGER)

    @classmethod
    @handle_exception
    def set_sync_readout_mode(cls):
        """
        Puts camera into edge trigger mode. Default camera mode for a z-stack in normal galvo scanning mode
        (dslm() in galvo commands).

        """
        cls.stop_live_acquisition()
        cls.set_property(cls._SENSOR_MODE_PROP,cls._AREA_SENSOR_MODE)
        cls.set_property(cls._TRIGGER_POLARITY_PROP, cls._POSITIVE_POLARITY)
        cls.set_property(cls._TRIGGER_SOURCE_PROP, cls._EXTERNAL_SOURCE)
        cls.set_property(cls._TRIGGER_ACTIVE_PROP, cls._SYNC_READOUT)
        
    @classmethod
    @handle_exception
    def set_lsrm_mode(cls, ili: float, num_lines: int):
        """
        Sets camera to lsrm mode with given internal line interval (ili) and 
        number of lines (num_lines) which are used to calculate exposure time.
        In this mode, the camera is synced to the laser position to exclude
        light from objects not directly in the laser's path. Please read our 
        lab's lightsheet readout mode guide or the Hamamatsu documentation
        for a full explanation.

        parameters:

        ili : float 
        Internal Line Interval. Sets the readout sweeping frequency of lsrm.

        num_lines : int
        sets the number of lines that are active at one time. Essentially sets the exposure
        of each line equal to num_lines.
        """
        cls.stop_live_acquisition()
        line_interval = ili*constants.S_TO_MS
        cls.set_property(cls._SENSOR_MODE_PROP, cls._LSRM_SENSOR_MODE)
        cls.set_property(cls._TRIGGER_POLARITY_PROP, cls._POSITIVE_POLARITY)
        cls.set_property(cls._TRIGGER_SOURCE_PROP, cls._EXTERNAL_SOURCE)
        cls.set_property(cls._TRIGGER_ACTIVE_PROP, cls._EDGE_TRIGGER)
        cls.set_property(cls._ILI_PROP, line_interval)
        core.set_exposure(cls.CAM_NAME, line_interval * int(num_lines))

    #helpers
    @classmethod
    @handle_exception
    def get_edge_trigger_exposure(cls, desired_exposure, framerate):
        """
        Takes desired exposure time and returns it if it's appropriate for edge trigger mode. If it's outside of the range
        of appropriate exposure times, returns closest limiting exposure. 
        
        The Hamamatsu documentation says that the maximum framerate is given by 1/(Vn/2*1H + Exp + 1H * 10) where Vn is the 
        number of lines (pixel rows), Exp is the exposure, and 1H is the readout of a single pixel row. From this, we can 
        solve for the exposure, which gives us max_exp = 1/framerate - readout_delay where readout_delay is the additional
        readout of pixel rows.
        
        Please see the framerate section of the Hamamatsu documentation for more details on this.
        """
        if not core.is_sequence_running():
            readout_delay = cls.get_edge_trigger_readout(core.get_image_height())
            max_exposure = (1/framerate - readout_delay)*constants.S_TO_MS
            exposure = general_functions.value_in_range(desired_exposure, cls.MIN_EXPOSURE, max_exposure)
        else:
            exposure = desired_exposure
        return exposure
    
    @classmethod
    @handle_exception
    def get_max_edge_trigger_exposure(cls, framerate):
        """
        Takes desired exposure time and returns it if it's appropriate for edge trigger mode. If it's outside of the range
        of appropriate exposure times, returns closest limiting exposure. 
        
        The Hamamatsu documentation says that the maximum framerate is given by 1/(Vn/2*1H + Exp + 1H * 10) where Vn is the 
        number of lines (pixel rows), Exp is the exposure, and 1H is the readout of a single pixel row. From this, we can 
        solver for the exposure, which gives us max_exp = 1/framerate - readout_delay where readout_delay is the additional
        readout of pixel rows.
        
        Please see the framerate section of the Hamamatsu documentation for more details on this.
        """
        readout_delay = cls.get_edge_trigger_readout(core.get_image_height())
        return (1/framerate - readout_delay)*constants.S_TO_MS

    @classmethod
    @handle_exception
    def get_edge_trigger_readout(cls, image_height):
        """
        This is the readout time plus delay from the framerate calculation in the Hamamatsu documentation.
        Symbolocally, this is 1H*(Vn/2 + 10) where1 H is the readout of one single row and Vn is the number of pixel rows.
        """
        return cls.READOUT_PER_ROW_S*(image_height/2 + cls.NUM_LINES_DELAY)
    
    @classmethod
    @handle_exception
    def set_binning(cls, binning: int):
        """
        Sets binning to given binning, Binning should be an integer: 1 for no binning, 2 for 2x2 binning
        or 4 for 4x4 binning.
        """
        cls.set_property("Binning", f"{binning}x{binning}")
        cls.wait_for_camera()


class Hamamatsu2(Hamamatsu):
    """
    Second Hamamatsu camera on Klamath, used only for dual-camera acquisitions (channels named in
    acquisition.imaging.DUAL_CAMERA_CHANNELS). Its device label is fixed because it is never the
    Micro-Manager Core-Camera at startup.
    """
    CAM_NAME = "HamamatsuHam_DCAM2"
