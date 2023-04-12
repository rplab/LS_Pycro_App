from enum import Enum
from utils import user_config, general_functions

class AdvSettings():
    """
    Class that holds advanced settings for acquisition.

    General idea of this class is to hold properties that the average user shouldn't need to worry about and
    that are reset between application sessions.

    ## Instance Attributes:
    
    #### z_stack_spectral_bool : bool
        If True, z-stacks will be spectral. A spectral z-stack takes an image in every channel before moving to 
        the next z-position. It is MUCH slower than a normal z-stack and should only be used if you need to. 
        Please see the Acquisition class for more details.

    #### speed_list : list[float]
        list of stage speeds (in um/s) that are available to the user for z-stacks. 30 should be the default.

    #### z_stack_stage_speed : float
        currently set stage speed (in um/s) to be used during z-stack

    #### z_stack_exposure : float
        exposure time for z-stacks. Note that this is a property, so _z_stack_exposure should not be directly 
        accessed. Read property and setter attributes for more details.

    #### video_spectral_bool : bool
        If True, videos will be spectral. Same as spectral z_stack except stage does notmove between spectral 
        images.

    #### acq_order : AcquisitionOrder()
        Enum that determines the acquisition order. See the AcquisitionOrder valuesfor more details.

    #### edge_trigger_bool : bool
        If True, camera is set to edge trigger mode. If False, camera is set to sync readout. See below 
        z_stack_exposure property and setter and Hamamatsu documentation for more details.

    #### lsrm_bool : bool
        If True, lightsheet readout mode is enabled. See SPIMGalvo lsrm(), lsrm methods in HardwareCommands, 
        and Hamamatsu documentation for more details.

    #### backup_directory_enabled : bool
        If True, backup_directory is enabled for acquisition. Path set in backup_directory will replace the 
        directory set in AcquisitionSettings in acquisition if space at that directory gets low during acquisition.

    #### backup_directory : str
        Second save path to be changed to if directory in AcquisitionSettings gets low during an acquisition. 
        Will only be used if backup_directory_enabled is True.
    """

    def __init__(self):
        self.speed_list: list[int] = [15, 30]
        self.z_stack_stage_speed: int = 30
        self.spectral_z_stack_enabled: bool = False
        self.spectral_video_enabled: bool = False
        self.acq_order = AcqOrder.TIME_SAMP
        self.backup_directory_enabled: bool = False
        self.backup_directory: str = "F:/"

    def write_to_config(self):
        user_config.write_class(self)

class AcqOrder(Enum):
    """
    Enum class to select acquisition order.
    
    ## enums:

    #### SAMP_TIME
        sample is iterated in outermost loop. This causes a full time series to be performed at each sample before 
        moving to the next.

    #### TIME_SAMP
        time_point is iterated in the outermost loop. the default acquisition order. For each time point, 
        each sample is imaged in sequence before moving to the next time point.
    """

    TIME_SAMP = 1
    SAMP_TIME = 2
    POS_TIME = 3