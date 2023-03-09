"""
This module contains all methods that interact with the camera as well as methods that calculate relevant
values for it. Please read the documnetation for more information on specific settings and properties. 
The camera is connected through Micro-Manager, and so all its properties are set with the Micro-Manager API.
Please see pycro.py for more information on the Micro-Manager API.

The Klamath setup uses the Hamamatsu C11440-22CU.

Hamamatsu manual (Download link of PDF. Check downloads.)

https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=&ved=2ahUKEwiBw9qNsZD7AhURKn0KHcDbDWQQFnoECAsQAQ&url=https%3A%2F%2Fwiki.umontreal.ca%2Fdownload%2Fattachments%2F189567146%2FHamamatsu_Orca%2520Flash%25204.0_V2_C11440-22CU_Instruction%2520Manual.pdf%3Fversion%3D1%26modificationDate%3D1627866006000%26api%3Dv2&usg=AOvVaw3vpbp7BfjOyA9mwO81xykH


Future changes:

- For now, since everything here is a constant, I didn't create a class to hold settings. If state is ever
added to this, should make a class to hold these.
"""

from hardware.exceptions_handle import handle_exception
from hardware.camera import Camera
from utils import constants, general_functions
from utils.pycro import studio, core


class Hamamatsu(Camera):
    #Can't seem to figure out what the max or min is for PCO. Isn't clear in documentation.
    MAX_EXPOSURE = 2000
    MIN_EXPOSURE = .010

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

    @classmethod
    @handle_exception
    def set_burst_mode(cls):
        """
        Sets the camera properties to its default properties. 
        
        Currently, this sets the trigger mode to Internal and sets the exposure time to the exposure provided.

        ### Parameters:
        
        #### exposure : int
            exposure time in ms. read the Hamamatsu documentation for what exposure
            times are allowed.
        """
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

        ### Parameters:

        #### exposure : int
            desired Exposure time in ms. Read the Hamamatsu documentation on what exposure
            times are allowed.

        #### framerate : int
            framerate of camera.
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
        Sets the camera properties for a z-stack in normal galvo scanning mode
        (dslm() in galvo commands). Returns actual set exposure time.

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
        This is fundamentally different from DSLM properties in two ways. 
        The sensor mode is set to progressive and we need to set an internal
        line interval. Please read the lightsheet readout mode guide for a 
        full explanation of this mode.

        Essentially, this is the LSRM analog of the set_dslm_camera_properties()
        method.

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
        core.set_exposure(line_interval * int(num_lines))

    #helpers
    @classmethod
    @handle_exception
    def get_edge_trigger_exposure(cls, desired_exposure, framerate):
        """
        Takes desired exposure time and returns it if it's appropriate for edge trigger mode. If it's outside of the range
        of appropriate exposure times, returns closest limiting exposure. 
        
        The Hamamatsu documentation says that the maximum framerate is given by 1/(Vn/2*1H + Exp + 1H * 10) where Vn is the 
        number of lines (pixel rows), Exp is the exposure, and 1H is the readout of a single pixel row. From this, we can 
        solver for the exposure, which gives us max_exp = 1/framerate - readout_delay where readout_delay is the additional
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
        if not core.is_sequence_running():
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

                