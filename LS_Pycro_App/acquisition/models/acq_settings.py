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
import numpy as np
import re
from copy import deepcopy

from LS_Pycro_App.acquisition.models.adv_settings import AdvSettings
from LS_Pycro_App.hardware import Camera
from LS_Pycro_App.utils import constants, user_config, pycro, general_functions
from LS_Pycro_App.utils.pycro import core


class Region():
    """
    Data class that stores properties that are specific to individual regions.

    ## Instance Attributes:

    #### x_pos : int 
        x_pos (in um)

    #### y_pos : int
        y_pos (in um)

    #### z_pos : int
        z_pos (in um)

    #### z_stack_bool : bool 
        If True, z-stacks will be enabled for the acquisition of this region.

    #### start_z_pos : int
        starting pos of z-stack (in um)

    #### end_z_pos : int
        end pos of z-stack (in um)

    #### step_size : int
        step size to be used during z-stack (in um)

    #### z_stack_channel_list : list[str]
        list of channels to be used for z-stack acquisition

    #### snap_bool : bool
        if True, snaps will be enabled for the acquisition of this region

    #### snap_exposure : int
        exposure time (in ms) to be used during snap

    #### snap_channel_list : list[str]
        list of channels to be used for snap acquisition

    #### video_bool : bool
        if True, snaps will be enabled for the acquisition of this region

    #### video_num_frames : int
        number of frames to be acquired in video acquisition

    #### video_exposure : int
        exposure time (in ms) to be used during video

    #### video_channel_list : list[str]
        list of channels to be used for video acquisition

    #### num_images : int
        number of images to be acquired at this region. set by update_num_images().
    """
    #default values don't matter much. Exposures are set to 20 ms, which is what I generally use.
    _x_pos: int = 0
    _y_pos: int = 0
    _z_pos: int = 0
    _z_stack_enabled: bool = False
    _z_stack_start_pos: int = 0
    _z_stack_end_pos: int = 0
    _z_stack_step_size: int = 1
    _z_stack_channel_list: list[str] = []
    _snap_enabled: bool = False
    _snap_exposure: float = 20.
    _snap_channel_list: list[str] = []
    _video_enabled: bool = False
    _video_num_frames: int = 100
    _video_exposure: float = 20.
    _video_channel_list: list[str] = []

    def __init__(self):
        self._x_pos: int = Region._x_pos
        self._y_pos: int = Region._y_pos
        self._z_pos: int = Region._z_pos
        self._z_stack_enabled: bool = Region._z_stack_enabled
        self._z_stack_start_pos: int = Region._z_stack_start_pos
        self._z_stack_end_pos: int = Region._z_stack_end_pos
        self._z_stack_step_size: int = Region._z_stack_step_size
        self._z_stack_channel_list: list[str] = deepcopy(Region._z_stack_channel_list)
        self._snap_enabled: bool = Region._snap_enabled
        self._snap_exposure: float = Region._snap_exposure
        self._snap_channel_list: list[str] = deepcopy(Region._snap_channel_list)
        self._video_enabled: bool = Region._video_enabled
        self._video_num_frames: int = Region._video_num_frames
        self._video_exposure: float = Region._video_exposure
        self._video_channel_list: list[str] = deepcopy(Region._video_channel_list)
        self._size_mb: float = 0

    #This setter pattern is used to store default values for created Region objects. 
    @property
    def x_pos(self):
        return self._x_pos
    
    @x_pos.setter
    def x_pos(self, value):
        self._x_pos = value
        Region._x_pos = value

    @property
    def y_pos(self):
        return self._y_pos
    
    @y_pos.setter
    def y_pos(self, value):
        self._y_pos = value
        Region._y_pos = value

    @property
    def z_pos(self):
        return self._z_pos
    
    @z_pos.setter
    def z_pos(self, value):
        self._z_pos = value
        Region._z_pos = value

    @property
    def z_stack_enabled(self):
        return self._z_stack_enabled
    
    @z_stack_enabled.setter
    def z_stack_enabled(self, value):
        self._z_stack_enabled = value
        Region._z_stack_enabled = value

    @property
    def z_stack_start_pos(self):
        return self._z_stack_start_pos
    
    @z_stack_start_pos.setter
    def z_stack_start_pos(self, value):
        self._z_stack_start_pos = value
        Region._z_stack_start_pos = value

    @property
    def z_stack_end_pos(self):
        return self._z_stack_end_pos
    
    @z_stack_end_pos.setter
    def z_stack_end_pos(self, value):
        self._z_stack_end_pos = value
        Region._z_stack_end_pos = value

    @property
    def z_stack_step_size(self):
        return self._z_stack_step_size
    
    @z_stack_step_size.setter
    def z_stack_step_size(self, value):
        self._z_stack_step_size = value
        Region._z_stack_step_size = value

    @property
    def z_stack_channel_list(self):
        AcqSettings.order_from_order_list(self._z_stack_channel_list)
        return self._z_stack_channel_list
    
    @z_stack_channel_list.setter
    def z_stack_channel_list(self, value):
        self._z_stack_channel_list = value
        Region._z_stack_channel_list = value

    @property
    def snap_enabled(self):
        return self._snap_enabled
    
    @snap_enabled.setter
    def snap_enabled(self, value):
        self._snap_enabled = value
        Region._snap_enabled = value

    @property
    def snap_exposure(self):
        return self._snap_exposure
    
    @snap_exposure.setter
    def snap_exposure(self, value):
        value = general_functions.value_in_range(value, Camera.MIN_EXPOSURE, Camera.MAX_EXPOSURE)
        self._snap_exposure = value
        Region._snap_exposure = value

    @property
    def snap_channel_list(self):
        AcqSettings.order_from_order_list(self._snap_channel_list)
        return self._snap_channel_list
    
    @snap_channel_list.setter
    def snap_channel_list(self, value):
        self._snap_channel_list = value
        Region._snap_channel_list = value

    @property
    def video_enabled(self):
        return self._video_enabled
    
    @video_enabled.setter
    def video_enabled(self, value):
        self._video_enabled = value
        Region._video_enabled = value

    @property
    def video_num_frames(self):
        return self._video_num_frames
    
    @video_num_frames.setter
    def video_num_frames(self, value):
        self._video_num_frames = value
        Region._video_num_frames = value

    @property
    def video_exposure(self):
        return self._video_exposure
    
    @video_exposure.setter
    def video_exposure(self, value):
        value = general_functions.value_in_range(value, Camera.MIN_EXPOSURE, Camera.MAX_EXPOSURE)
        self._video_exposure = value
        Region._video_exposure = value

    @property
    def video_channel_list(self):
        AcqSettings.order_from_order_list(self._video_channel_list)
        return self._video_channel_list
    
    @video_channel_list.setter
    def video_channel_list(self, value):
        self._video_channel_list = value
        Region._video_channel_list = value

    @property
    def size_mb(self):
        image_size = core.get_image_width()*core.get_image_height()*core.get_bytes_per_pixel()*constants.B_TO_MB
        self._size_mb = image_size*self.num_images
        return self._size_mb

    @property
    def num_images(self):
        num_images = 0
        if self.z_stack_enabled:
            num_images += len(self.z_stack_channel_list)*self.z_stack_num_frames
        if self.snap_enabled:
            num_images += len(self.snap_channel_list)
        if self.video_enabled:
            num_images += len(self.video_channel_list)*self.video_num_frames
        self._num_images = num_images
        return num_images
    
    @property
    def z_stack_num_frames(self):
        num_frames = int(np.ceil(abs(self.z_stack_end_pos - self.z_stack_start_pos)/self.z_stack_step_size))
        self._z_stack_num_frames = num_frames
        return num_frames

    @property
    def imaging_enabled(self):
        return self.snap_enabled or self.video_enabled or self.z_stack_enabled
    
    #config api methods
    def init_from_config(self, fish_num: int, region_num: int) -> bool:
        return user_config.init_class(self, Region.config_section(fish_num, region_num))
    
    def write_to_config(self, fish_num, region_num):
        user_config.write_class(self, Region.config_section(fish_num, region_num))

    def config_section(fish_num, region_num):
        if isinstance(fish_num, str):
            return f"Fish {fish_num} Region {region_num}"
        else:
            return f"Fish {fish_num + 1} Region {region_num + 1}"


class Fish():
    """
    Class that holds settings attached to a single fish. Includes notes on fish as well, list of 
    Region instances, and total number of images in acquisition of fish.

    ## Instance Attributes:

    #### self.not_config_props : list[str]
        list of instance attributes that should not be written to config

    #### region_list : list[Region]
        List of instances of Region

    #### fish_type : str
        type of fish being imaged (genotype, condition, etc)

    #### age : str
        fish age

    #### inoculum : str
        inoculum of fish

    #### add_notes : str
        any additional notes on fish

    #### num_images : int
        number of images to be acquired at this fish.

    ## Instance Methods

    #### remove_region(region_num)
        removes region from region_list at given region_num index

    #### append_blank_region()
        appends new instance of Region to region_list
    """
    NOT_CONFIG_PROPS = ["region_list"]

    _fish_type: str = ""
    _age: str = ""
    _inoculum: str = ""
    _add_notes: str = ""

    def __init__(self):
        self.region_list: list[Region] = []
        self._num_regions: int = len(self.region_list)
        self._fish_type: str = Fish._fish_type
        self._age: str = Fish._age
        self._inoculum: str = Fish._inoculum
        self._add_notes: str = Fish._add_notes
        self._size_mb: float = 0

    @property
    def num_regions(self):
        self._num_regions = len(self.region_list)
        return self._num_regions
    
    @property
    def fish_type(self):
        return self._fish_type
    
    @fish_type.setter
    def fish_type(self, value):
        self._fish_type = value
        Fish._fish_type = value
    
    @property
    def age(self):
        return self._age
    
    @age.setter
    def age(self, value):
        self._age = value
        Fish._age = value

    @property
    def inoculum(self):
        return self._inoculum
    
    @inoculum.setter
    def inoculum(self, value):
        self._inoculum = value
        Fish._inoculum= value

    @property
    def add_notes(self):
        return self._add_notes
    
    @add_notes.setter
    def add_notes(self, value):
        self._add_notes = value
        Fish._add_notes= value

    @property
    def num_images(self):
        fish_num_images = 0
        for region in self.region_list:
            region.num_images
            fish_num_images += region.num_images
        self._num_images = fish_num_images
        return fish_num_images
    
    @property
    def imaging_enabled(self):
        for region in self.region_list:
            if region.imaging_enabled:
                return True
        else:
            return False

    @property
    def size_mb(self):
        image_size = core.get_image_width()*core.get_image_height()*core.get_bytes_per_pixel()*constants.B_TO_MB
        self._size_mb = image_size*self.num_images
        return self._size_mb

    #region_list methods
    def append_blank_region(self) -> Region:
        region = Region()
        self.region_list.append(region)
        return region
    
    def update_region_list(self, region_num, region):
        try:
            self.region_list[region_num] = region
        except IndexError:
            self.region_list.append(region)
    
    def remove_region(self, region_num):
        del self.region_list[region_num]

    #config api methods
    def init_from_config(self, fish_num: int) -> bool:
        return user_config.init_class(self, Fish.config_section(fish_num))

    def write_to_config(self, fish_num: int):
        user_config.write_class(self, Fish.config_section(fish_num))

    def config_section(fish_num: int):
        if isinstance(fish_num, str):
            return f"Fish {fish_num} Notes"
        else:
            return f"Fish {fish_num + 1} Notes"


class AcqSettings():
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
    core_channel_list: list[str] = pycro.get_channel_list()
    _channel_order_list: list[str] = deepcopy(core_channel_list)

    def __init__(self):
        self.adv_settings: AdvSettings = AdvSettings()
        self.fish_list: list[Fish] = []
        self.time_points_enabled: bool = False
        self.time_points_interval_sec: int = 0
        self.directory: str = "C:/"
        self.researcher: str = ""
        self._num_fish: int = self.num_fish
        self._num_time_points: int = 1
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
        AcqSettings._channel_order_list = value

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
    def num_fish(self):
        self._num_fish = len(self.fish_list)
        return self._num_fish

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
    def images_per_time_point(self):
        images_per_time_point = 0
        for fish in self.fish_list:
            images_per_time_point += fish.num_images
        self._images_per_time_point = images_per_time_point
        return images_per_time_point
    
    @property
    def total_num_images(self):
        if self.time_points_enabled:
            self._total_num_images = self.images_per_time_point*self.num_time_points
        else:
            self._total_num_images = self.images_per_time_point
        return self._total_num_images
    
    @property
    def imaging_enabled(self):
        for fish in self.fish_list:
            if fish.imaging_enabled:
                return True
        else:
            return False
        
    @property
    def size_mb(self):
        self._size_mb = self.total_num_images*self.image_size_mb
        return self._size_mb

    #fish_list methods
    def append_blank_fish(self) -> Fish:
        fish = Fish()
        self.fish_list.append(fish)
        return fish
    
    def update_fish_list(self, fish_num: int, fish: Fish):
        try:
            self.fish_list[fish_num] = fish
        except IndexError:
            self.fish_list.append(fish)

    def remove_fish(self, fish_num: int):
        del self.fish_list[fish_num]

    #misc api methods
    def is_step_size_same(self):
        step_size = self.get_first_step_size()
        for fish in self.fish_list:
            for region in fish.region_list:
                if region.z_stack_step_size != step_size and region.z_stack_enabled:
                    return False
        else:
            return True
        
    def get_first_step_size(self):
        for fish in self.fish_list:
            for region in fish.region_list:
                if region.z_stack_enabled:
                    return region.z_stack_step_size
        
    def reorder_channel_lists(self):
        """
        reorders region channel lists to match channel_order_list
        """
        for fish in self.fish_list:
            for region in fish.region_list:
                self.order_from_order_list(region.snap_channel_list)
                self.order_from_order_list(region.z_stack_channel_list)
                self.order_from_order_list(region.video_channel_list)

    #config api methods
    def init_from_config(self):
        user_config.init_class(self)
        self._init_channel_order_list()
        self._init_fish_list_from_config()
        
    def write_to_config(self):
        user_config.write_class(self)
        user_config.write_class(self.adv_settings)
        self._write_fish_list_to_config()

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
    def _init_fish_list_from_config(self):
        fish_num = 0
        while True:
            fish = Fish()
            if fish.init_from_config(fish_num):
                self.fish_list.append(fish)
            else:
                break
            self._init_regions_from_config(fish, fish_num)
            fish_num += 1
    
    def _init_regions_from_config(self, fish: Fish, fish_num: int):
        region_num = 0
        while True:
            region = Region()
            if region.init_from_config(fish_num, region_num):
                fish.region_list.append(region)
            else:
                break
            region_num += 1 

    def _remove_fish_sections(self):
        """
        Checks for all sections that match format of region_section and fish_section and removes them.
        Example: "Fish 1 Notes" is of the form f"Fish {'[0-9]'} Notes", as is "Fish 150 Notes",
        so bool(re.match()) returns True.
        """
        for section in user_config.sections():
            region_section_bool = bool(re.match(Region.config_section('[0-9]', '[0-9]'), section))
            fish_section_bool = bool(re.match(Fish.config_section('[0-9]'), section))
            if region_section_bool or fish_section_bool:
                user_config.remove_section(section)
    
    def _write_fish_list_to_config(self):
        self._remove_fish_sections()
        for fish_num, fish in enumerate(self.fish_list):
            fish.write_to_config(fish_num)
            for region_num, region in enumerate(fish.region_list):
                region.write_to_config(fish_num, region_num)

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
