from LS_Pycro_App.utils import user_config, general_functions


class GalvoSettings(object):
    """
    Class that holds all settings changed by Spim Galvo Dialog. Also holds all business
    logic associated with setting said values.

    Every attrubute in this class is set with a property/setter

    ## Instance Attributes:

    #### focus:float
        focus offset of laser (voltage offset to x-galvo mirror in mV)

    #### dslm_offset:float
        vertical offset of laser (voltage offset sent to y-galvo mirror in mV) used in dslm() anddslm_not_scanning() 
        in SPIMCommands

    #### dslm_scan_width:float
        Scanning range of laser (voltage range of scanning sample sent to y-galvo mirror) used in dslm() in SPIMCommands

    #### lsrm_cur_pos:float
        Current position of laser to be used for setting lsrm_upper and lsrm_lower. Used in lsrm_not_scanning() 
        in SPIMCommands

    #### lsrm_upper:float
        upper limit of galvo scanning range in lsrm() in SPIMCommands. Note that it's the upper limit by value, so when 
        lsrm_upper is set correctly, the laser will actually be at the bottom of the camera feed.

    #### lsrm_lower:float
        lower limit of galvo scanning range in lsrm() in SPIMCommands

    #### lsrm_framerate:float
        framerate of camera in lightsheet readout mode.

    #### lsrm_laser_delay:float
        laser delay in ms in lsrm()

    #### lsrm_cam_delay:float
        cam delay in ms in lsrm()

    #### lsrm_ili:float
        internal line interval determined by calculation in lsrm(). Used as a parameter in set_lsrm_camera_properties()
        in camera module.

    #### lsrm_num_lines:int
        number of lines in lightsheet readout mode. Used as a parameter in set_lsrm_camera_properties()
        in camera module.

    ##Future Changes:

    - I decided not to abstract this class because currently the Klamath setup is the only one with computer-based
    galvo control. If Willamette ever gets this, will have to think more about abstraction.
    """
    FOCUS_CHANNEL = "Dev1/ao2"
    OFFSET_CHANNEL = "Dev1/ao3"
    CAM_CHANNEL = "Dev1/Ctr0"
    PLC_INPUT_CHANNEL = 'PFI0'
    DSLM_NUM_SAMPLES = 600
    DSLM_FREQ = 600
    DSLM_SAMPLE_RATE = DSLM_NUM_SAMPLES*DSLM_FREQ
    BASE_LSRM_NUM_SAMPLES = 2048
    #NIDAQ default pulse time is .01 seconds, which is too long considering the maximum framerate is 100 fps, or 1 ms exposure
    PULSE_TIME_S = .0001

    OFFSET_BOT_LIMIT = -3
    OFFSET_TOP_LIMIT = 3
    FOCUS_BOT_LIMIT = -3
    FOCUS_TOP_LIMIT = 3
    WIDTH_BOT_LIMIT = 0
    WIDTH_TOP_LIMIT = 2 * OFFSET_TOP_LIMIT
    FRAMERATE_BOT_LIMIT = 1
    FRAMERATE_TOP_LIMIT = 40
    DELAY_BOT_LIMIT = 0.
    DELAY_TOP_LIMIT = 2.
    NUM_LINES_BOT_LIMIT = 1
    NUM_LINES_TOP_LIMIT = 80
    #framerate-laser_delay pairs for lsrm mode. Found empirically.
    LASER_DELAYS = {5: 2., 10: 1., 20: 0.45, 30: 0.3, 40: 0.25}

    def __init__(self):
        self.is_lsrm = False
        self.focus = 0.
        self._dslm_offset = 0.
        self._dslm_scan_width = 1.1
        self._lsrm_cur_pos = 0.
        self._lsrm_upper = 0.
        self._lsrm_lower = 0.
        self._lsrm_framerate = 15
        self._lsrm_laser_delay = 0.500
        self._lsrm_cam_delay = 0.
        self._lsrm_num_lines = 30
        self.init_from_config()

    @property
    def focus(self):
        return self._focus

    @focus.setter
    def focus(self, value):
        self._focus = round(general_functions.value_in_range(value, self.FOCUS_BOT_LIMIT, self.FOCUS_TOP_LIMIT), 3)

    @property
    def dslm_offset(self):
        return self._dslm_offset

    @dslm_offset.setter
    def dslm_offset(self, value):
        self._dslm_offset = round(general_functions.value_in_range(
            value, self.OFFSET_BOT_LIMIT, self.OFFSET_TOP_LIMIT), 3)

    @property
    def dslm_scan_width(self):
        return self._dslm_scan_width

    @dslm_scan_width.setter
    def dslm_scan_width(self, value):
        self._dslm_scan_width = round(general_functions.value_in_range(
            value, self.WIDTH_BOT_LIMIT, self.WIDTH_TOP_LIMIT), 3)

    @property
    def lsrm_cur_pos(self):
        return self._lsrm_cur_pos

    @lsrm_cur_pos.setter
    def lsrm_cur_pos(self, value):
        self._lsrm_cur_pos = round(general_functions.value_in_range(
            value, self.OFFSET_BOT_LIMIT, self.OFFSET_TOP_LIMIT), 3)

    @property
    def lsrm_upper(self):
        return self._lsrm_upper

    @lsrm_upper.setter
    def lsrm_upper(self, value):
        self._lsrm_upper = round(general_functions.value_in_range(
            value, self.OFFSET_BOT_LIMIT, self.OFFSET_TOP_LIMIT), 3)

    @property
    def lsrm_lower(self):
        return self._lsrm_lower

    @lsrm_lower.setter
    def lsrm_lower(self, value):
        self._lsrm_lower = round(general_functions.value_in_range(
            value, self.OFFSET_BOT_LIMIT, self.OFFSET_TOP_LIMIT), 3)

    @property
    def lsrm_framerate(self):
        return self._lsrm_framerate

    @lsrm_framerate.setter
    def lsrm_framerate(self, value):
        self._lsrm_framerate = int(general_functions.value_in_range(
            value, self.FRAMERATE_BOT_LIMIT, self.FRAMERATE_TOP_LIMIT))

    @property
    def lsrm_cam_delay(self):
        return self._lsrm_cam_delay

    @lsrm_cam_delay.setter
    def lsrm_cam_delay(self, value):
        self._lsrm_cam_delay = round(general_functions.value_in_range(
            value, self.DELAY_BOT_LIMIT, self.DELAY_TOP_LIMIT), 3)

    @property
    def lsrm_laser_delay(self):
        framerates = list(self.LASER_DELAYS.keys())
        #finds closest framerate and returns associated delay value in LASER_DELAYS dict
        return self.LASER_DELAYS[min(framerates, key = lambda f: abs(f-self.lsrm_framerate))]

    @property
    def lsrm_num_lines(self):
        return self._lsrm_num_lines

    @lsrm_num_lines.setter
    def lsrm_num_lines(self, value):
        self._lsrm_num_lines = int(general_functions.value_in_range(
            value, self.NUM_LINES_BOT_LIMIT, self.NUM_LINES_TOP_LIMIT))
    
    @property
    def lsrm_num_samples(self):
        return self.lsrm_num_lines + self.BASE_LSRM_NUM_SAMPLES
        
    @property
    def lsrm_sample_rate(self):
        return self.lsrm_num_samples*(self.lsrm_framerate + 1)

    @property
    def lsrm_ili(self):
        return 1/(self.lsrm_sample_rate)

    def write_to_config(self):
        user_config.write_class(self)

    def init_from_config(self):
        user_config.init_class(self)
