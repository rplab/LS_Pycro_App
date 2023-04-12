from hardware.exceptions_handle import handle_exception
from hardware.camera import Camera
from utils.pycro import studio, core

class Camera(Camera):
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
        """
        Sets the camera properties to its default properties. 
        
        """
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
            