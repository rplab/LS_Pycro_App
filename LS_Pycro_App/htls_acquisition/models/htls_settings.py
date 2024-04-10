"""
The "Model" part of the acquisition package. Contains all classes that hold properties to be used during image 
acquisition (except advanced settings, which is held in its own module).

Notes:

- If adding a fish or region to these lists, use append unless you're replacing an element
at an index.

- All "exposure" attributes are units of ms and all "pos" attributes are in um.

- If new settings are needed in the future for acquisitions, I HIGHLY reccomend inheriting one of these already
created classes instead of adding functionality to them. This will ensure no required attributes are missing.

Future Changes:
- More input validation for values. Currently, most validation is done on the PyQt5 side.
  
- consider using dataclass decorator for these. Would make it much prettier and field methods could be useful.
"""
from copy import deepcopy

from LS_Pycro_App.acquisition.models.acq_settings import AdvSettings, Region, Fish
from LS_Pycro_App.utils import constants, user_config, pycro
from LS_Pycro_App.utils.pycro import core


class HTLSSettings():
    """
    Data class that stores properties that apply to the entire image acquisition. Also includes list that holds Fish
    instances, which are the main objects (along with Region instances) used during an image acquisition.

    ## Class Attributes:

    #### image_width : int
        width of image in pixels according to MM

    #### image_height : int
        height of image in pixels according to MM

    #### image_size_mb : float
        image size according to MM (sort of). Calculatiom I use is just width*height*(bit_depth)/10**6

    ## Instance Attributes:

    #### fish_list : list[Fish]
        list that holds instances of Fish.

    #### adv_settings : AdvancedSettings
        instance of AdvancedSettings

    #### total_num_images : int
        total number of images in acquisition.

    #### time_points_bool : bool
        if True, a time series based on num_time_points and time_points_interval will be enabled.

    #### num_time_points : int
        number of time points. Note that this is a property and that _num_time_points shouldnever be accessed directly.

    #### time_points_interval_min : int
        interval (in minutes) between time points in time series. If set to 0 (or if acquisition of a single time 
        point takes longer than the interval), acquisition of the next time point will start immediately.

    #### channel_order_list : list[str]
        channel order acquisition used during acquisition. If multiple channels are selectedfor a specific type of 
        image acquisition in a Region instance (video, snap, z-stack, etc.), the channels will be acquired in this 
        order.

    #### directory : str
        path where acquisition is to be saved.
    
    #### researcher : str
        name of researcher
    
    ## Instance Methods:

    #### remove_fish(fish_num)
        removes fish at given fish_num index.

    #### append_blank_fish()
        Appends new Fish() object to self.fish_list
    """
    NOT_CONFIG_PROPS = ["fish_list", "adv_settings"]
    FISH_SETTINGS_SECTION = "Fish Settings"
    REGION_SETTINGS_SECTION = "Region Settings"
    core_channel_list: list[str] = pycro.get_channel_list()
    _channel_order_list: list[str] = deepcopy(core_channel_list)

    def __init__(self):
        self.adv_settings: AdvSettings = AdvSettings()
        self.time_points_enabled: bool = False
        self.time_points_interval_sec: int = 0
        self.directory: str = "C:/"
        self.researcher: str = ""
        self.fish_settings = Fish()
        self.region_settings = Region()
        self._num_fish: int = 0
        self._image_width: int = core.get_image_width()
        self._image_height: int = core.get_image_height()
        self._bytes_per_pixel: int = core.get_bytes_per_pixel()
        self._image_size_mb: float = self.image_size_mb
        self._images_per_time_point: int = 0
        self._total_num_images: int = 0
        self._size_mb: float = 0
        self.init_from_config()

    @property
    def channel_order_list(self):
        return self._channel_order_list
    
    @channel_order_list.setter
    def channel_order_list(self, value):
        self._channel_order_list = value
        self.reorder_channel_lists()
        HTLSSettings._channel_order_list = value

    @property
    def num_time_points(self):
        return self._num_time_points
    
    @num_time_points.setter
    def num_time_points(self, value):
        if value < 1:
            self._num_time_points = 1
        else:
            self._num_time_points = value

    @property
    def image_width(self):
        self._image_width = core.get_image_width()
        return self._image_width
    
    @property
    def image_height(self):
        self._image_height = core.get_image_height()
        return self._image_height

    @property
    def bytes_per_pixel(self):
        self._bytes_per_pixel = core.get_bytes_per_pixel()
        return self._bytes_per_pixel

    @property
    def image_size_mb(self):
        self._image_size_mb = self.image_width*self.image_height*self.bytes_per_pixel*constants.B_TO_MB
        return self._image_size_mb
    
    @property
    def imaging_enabled(self):
        return self.fish_settings.imaging_enabled
        
    def reorder_channel_lists(self):
        """
        reorders region channel lists to match channel_order_list
        """
        self.order_from_order_list(self.region_settings.snap_channel_list)
        self.order_from_order_list(self.region_settings.z_stack_channel_list)
        self.order_from_order_list(self.region_settings.video_channel_list)

    #config api methods
    def init_from_config(self):
        user_config.init_class(self)
        self._init_fish_settings_from_config()
        self._init_region_settings_from_config()
        self._init_channel_order_list()
        
    def write_to_config(self):
        user_config.write_class(self)
        user_config.write_class(self.fish_settings, HTLSSettings.FISH_SETTINGS_SECTION)
        user_config.write_class(self.region_settings, HTLSSettings.REGION_SETTINGS_SECTION)
        user_config.write_class(self.adv_settings)

    #api class methods
    @classmethod
    def order_from_order_list(cls, lst: list):
        """
        arranges lst by order of channel_order_list
        """
        channel_num = 0
        for channel in cls._channel_order_list:
            if channel in lst:
                cur_pos = lst.index(channel)
                if cur_pos != channel_num:
                    lst[channel_num], lst[cur_pos] = lst[cur_pos], lst[channel_num]
                channel_num += 1

    #config helpers
    def _init_fish_settings_from_config(self):
        user_config.init_class(self.fish_settings, HTLSSettings.FISH_SETTINGS_SECTION)

    def _init_region_settings_from_config(self):
        user_config.init_class(self.region_settings, HTLSSettings.REGION_SETTINGS_SECTION)

    #misc privates
    def _init_channel_order_list(self):
        """
        Initializes channel order list so that all channels in the core list are in the order list, since core channel
        list may change between sessions.
        """
        self.core_channel_list = pycro.get_channel_list()
        for channel in self.channel_order_list:
            if channel not in self.core_channel_list:
                self.channel_order_list = deepcopy(self.core_channel_list)
                break
        else:
            for channel in self.core_channel_list:
                if channel not in self.channel_order_list:
                    self.channel_order_list.append(channel)
