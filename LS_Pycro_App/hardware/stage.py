import logging
import numpy as np
from hardware import Plc
from hardware.exceptions_handle import handle_exception
from utils import constants
from utils.abc_attributes_wrapper import abstractattributes
from utils.pycro import core

@abstractattributes
class Stage():
    """
    You might be wondering, "Jonah, why is this a class if there isn't an __init__() method?"
    The answer is this was originally a module in the old versions of the light sheet code. When
    I decided to combine the two light sheet programs into one, I wanted to accomplish two things:
    
    1. Abstract the shared code 

    2. Make an interface that's easy to inherit
    
    Since the hardware of the two microscopes is almost identical, I was able
    to abstract away almost everything, the only differences being the "abstract attributes" below.
    As for the interface part, if this were a module, changing the variables at the module level
    would be 

    Now, Python doesn't inherently have abstract attributes (you would need to set abstract properties, 
    which I think would be more confusing and ugly), so I decided to write a class wrapper to do so! This
    wrapper makes it so if this class is inherited and the declared attributes below are not defined at runtime,
    the program will not run (control+click on the @abstractattributes line above to see this implementation). 
    If I were to have kept this as a module, there would be no way to enforce the definition of these attributes, 
    meaning the program would run until it attempts to access one of these attributes and then crash.

    Admittedly, the program crashing at attribute-access would probably suffice, though I shudder at the 
    possibility of an attribute being declared but not defined that is accessed during an important experiment
    that causes the acquisition to fail. Thus, here we are.

    Now, that explains the class part, but why is there no __init__() method? Short answer: These hardware classes 
    are meant to be used as modules. __init__() is unecessary because these classes don't change state throughout
    runtime and each class represents exactly one hardware device, so it doesn't really make sense to have
    multiple classes representing the same hardware device UNLESS there was some reason to have two different
    sets of properties for the same device, which there currently isn't! It's worth noting there's no reason 
    any of these classes COULDN'T be instatiated. However, there is also no reason to, and I believe not 
    instantiating them more correctly reflects their utility as hardware modules.
    """
    #"abstract attributes" Interpreter will throw an error if the following aren't declared.
    STAGE_SERIAL_LABEL : str
    _X_AXIS_LABEL : str
    _Y_AXIS_LABEL : str
    _Z_AXIS_LABEL : str
    _INITIALIZE_SCAN_AXES : str
    _START_SCAN_COMMAND  : str
    _SCANR_COMMAND_START: str
    _SCANV_COMMAND : str
    _JOYSTICK_AXIS_RESET_COMMAND : str
    _JOYSTICK_Z_SPEED_COMMAND : str
    
    _logger = logging.getLogger(__name__)
    XY_STAGE_NAME : str = core.get_xy_stage_device()
    Z_STAGE_NAME : str = core.get_focus_device()

    _SERIAL : str = "SerialCommand"
    _SERIAL_NUM_DECIMALS : int = 6
    _JOYSTICK_ENABLE : str = "J X+ Y+ Z+"
    _JOYSTICK_Z_SPEED : str = "JSSPD Z=50"

    _DEFAULT_STAGE_SPEED_UM_PER_S : int = 1000
    #um buffer added to SCAN command so that camera takes enough images
    _BASE_Z_STACK_BUFFER : int = 2
    #number of um per um increase in buffer. Found empirically (reluctantly). See _get_z_stack_buffer().
    _UM_PER_UM_BUFFER = 92


    @classmethod
    def wait_for_xy_stage(cls):
        """
        Makes core wait for XY stage to become unbusy
        """
        core.wait_for_device(cls.XY_STAGE_NAME)
        cls._logger.info("Waiting for xy stage")

    @classmethod
    def wait_for_z_stage(cls):
        """
        Makes core wait for Z stage to become unbusy
        """
        core.wait_for_device(cls.Z_STAGE_NAME)
        cls._logger.info("Waiting for z stage")

    @classmethod
    def send_serial_command_to_stage(cls, command):
        """
        Makes core wait for Z stage to become unbusy
        """
        core.set_property(cls.STAGE_SERIAL_LABEL, cls._SERIAL, command)
        cls._logger.info(f"Serial command {command} sent to stage")

    @classmethod
    @handle_exception
    def set_x_stage_speed(cls, speed):
        """
        Sets x-stage speed

        ### Parameters:

        #### x_speed
            stage speed in um/s
        """
        cls.wait_for_xy_stage()
        #Since X and Z stages are swapped, must set Z-axis speed for X-axis speed change.
        cls.send_serial_command_to_stage(f"SPEED {cls._X_AXIS_LABEL}={round(speed*constants.UM_TO_MM, cls._SERIAL_NUM_DECIMALS)}")
        cls._logger.info(f"x stage speed set to {speed} um/s")

    @classmethod
    @handle_exception
    def set_y_stage_speed(cls, speed):
        """
        Sets y-stage speed

        ### Parameters:

        #### x_speed
            stage speed in um/s
        """
        cls.wait_for_xy_stage()
        cls.send_serial_command_to_stage(f"SPEED {cls._Y_AXIS_LABEL}={round(speed*constants.UM_TO_MM, cls._SERIAL_NUM_DECIMALS)}")
        cls._logger.info(f"y stage speed set to {speed} um/s")

    @classmethod
    @handle_exception
    def set_z_stage_speed(cls, speed):
        """
        Sets z-stage speed

        ### Parameters:

        #### speed
            stage speed in um/s
        """
        cls.wait_for_z_stage()
        cls.send_serial_command_to_stage(f"SPEED {cls._Z_AXIS_LABEL}={round(speed*constants.UM_TO_MM, cls._SERIAL_NUM_DECIMALS)}")
        cls._logger.info(f"z stage speed set to {speed} um/s")

    @classmethod
    @handle_exception
    def initialize_scan(cls, start_z: int, end_z: int):
        """
        Performs setup for stage SCAN command. 
        
        Please read the ASI manual for more details on SCAN:
        http://www.asiimaging.com/downloads/manuals/Operations_and_Programming_Manual.pdf
        
            An ASI stage scan is achieved by doing the following:

        1. Scan properties are set as "2 SCAN Y=0 Z=0 F=0". This is simply
            to tell the stage what axis will be scanning. In our case, we're
            scanning along the z-axis
        2. Positions are set with SCANR X=[StartPosition] Y=[EndPosition]
            where positions are in units of mm. SCANR means raster scan.
        3. "SCAN" is sent. When the stage reaches the start position, the TTL 
            port on the stage goes high. This is what triggers the PLC to pulse. 
            Once it reaches the end position, the TTL goes low and the stage resets 
            to the start position.

        ### Parameters:

        #### start_z : int
            scan start position in um

        #### end_z : int
            scan end position in um

        #### scan_speed
            scan speed in um/s
        """
        cls._send_scan_setup_commands(start_z, end_z)
        cls._logger.info("scan parameters have been set")

    #initialize_scan helpers
    @classmethod
    def _send_scan_setup_commands(cls, start_z, end_z):
        scan_r_command = cls._get_scan_r_command(start_z, end_z)
        cls.send_serial_command_to_stage(cls._INITIALIZE_SCAN_AXES)
        cls.send_serial_command_to_stage(scan_r_command)
        cls.send_serial_command_to_stage(cls._SCANV_COMMAND)

    @classmethod
    def _get_scan_r_command(cls, start_z, end_z):
        start_z_mm = round(start_z*constants.UM_TO_MM, cls._SERIAL_NUM_DECIMALS)
        end_z_mm = round(cls._get_end_z_position(start_z, end_z)*constants.UM_TO_MM, cls._SERIAL_NUM_DECIMALS)
        return f"{cls._SCANR_COMMAND_START} X={start_z_mm} Y={end_z_mm}"

    @classmethod
    def _get_end_z_position(cls, start_z, end_z):
        buffer = cls._get_z_stack_buffer(start_z, end_z)
        if start_z < end_z:
            end = end_z + buffer
        else:
            end = end_z - buffer
        return end

    @classmethod
    def _get_z_stack_buffer(cls, start_z, end_z):
        #This buffer... oh this buffer. Essentially, the stage TTL signal that goes HIGH
        #while the stage is moving during the SCAN command does not stay HIGH long enough.
        #For every ~92 microns in a scan, you must add 1 um to the buffer to make sure the
        #TTL is HIGH long enough for the camera to take enough images. 
        z_stack_range = cls._get_z_stack_range(start_z, end_z)
        return cls._BASE_Z_STACK_BUFFER + int(np.floor(z_stack_range/cls._UM_PER_UM_BUFFER))

    @classmethod
    def _get_z_stack_range(cls, z_start, z_end):
        return abs(z_start - z_end)

    @classmethod
    @handle_exception
    def scan_start(cls, stage_speed: float):
        """
        Sends SCAN command to the ASI stage to begin scan based on
        the properties set with scan_setup().

        This command tends to reset some of the settings of the joystick,
        so generally it's a good idea to call reset_joystick() after the scan
        is over.
        """
        cls.wait_for_xy_stage()
        cls.wait_for_z_stage()

        corrected_speed = Plc.get_true_z_stack_stage_speed(stage_speed)
        cls.set_z_stage_speed(corrected_speed)

        cls.send_serial_command_to_stage(cls._START_SCAN_COMMAND)
        cls._logger.info("Scan started")
        return corrected_speed
                
    @classmethod
    @handle_exception
    def move_stage(cls, x_pos, y_pos, z_pos):
        """
        Sets stage to the position specified by parameters x_pos, y_pos, z_pos (in um)
        """
        cls.set_x_stage_speed(cls._DEFAULT_STAGE_SPEED_UM_PER_S)
        cls.set_y_stage_speed(cls._DEFAULT_STAGE_SPEED_UM_PER_S)
        cls.set_z_stage_speed(cls._DEFAULT_STAGE_SPEED_UM_PER_S)

        #This section is to ensure capillaries don't hit the objective. These conditions
        #should be changed to match the geometry of the holder.
        current_x_position = cls.get_x_position()
        if current_x_position > x_pos:
            cls.set_z_position(z_pos)
            cls.wait_for_z_stage()
            cls.set_xy_position(x_pos, y_pos)
            cls.wait_for_xy_stage()
        else:
            cls.set_xy_position(x_pos, y_pos)
            cls.wait_for_xy_stage()
            cls.set_z_position(z_pos)
            cls.wait_for_z_stage()

        cls._logger.info(f"Stage position set to ({x_pos}, {y_pos}, {z_pos})")
            
    @classmethod
    @handle_exception
    def set_x_position(cls, x_pos):
        """
        Sets stage X-axis to x_pos (in um)
        """
        cls.wait_for_xy_stage()
        cls.set_x_stage_speed(cls._DEFAULT_STAGE_SPEED_UM_PER_S)
        #ASI MOVE (M) command takes position in tenths of microns, so multiply by 10       
        cls.send_serial_command_to_stage(f"M {cls._X_AXIS_LABEL}={int(x_pos)*constants.TO_TENTHS}")
        cls._logger.info(f"Stage x position set to {x_pos} um")

    @classmethod
    @handle_exception
    def set_y_position(cls, y_pos):
        """
        Sets stage Y-axis to y_pos (in um)
        """
        cls.wait_for_xy_stage()
        cls.set_y_stage_speed(cls._DEFAULT_STAGE_SPEED_UM_PER_S)      
        cls.send_serial_command_to_stage(f"M {cls._Y_AXIS_LABEL}={int(y_pos)*constants.TO_TENTHS}")
        cls._logger.info(f"Stage y position set to {y_pos} um")

    @classmethod
    def set_xy_position(cls, x_pos, y_pos):
        """
        Sets xy position of stage (in um). Setting both at the same time makes it so both stages will move at the same time. 
        """
        cls.set_x_stage_speed(cls._DEFAULT_STAGE_SPEED_UM_PER_S)
        cls.set_y_stage_speed(cls._DEFAULT_STAGE_SPEED_UM_PER_S)
        core.set_xy_position(x_pos, y_pos)
        cls._logger.info(f"Stage xy position set to ({x_pos}, {y_pos}) um")

    @classmethod
    @handle_exception
    def set_z_position(cls, z_pos):
        """
        Sets stage Z-axis to z_pos (in um)
        """
        cls.wait_for_z_stage()
        cls.set_z_stage_speed(cls._DEFAULT_STAGE_SPEED_UM_PER_S)
        #z-position is set through the core because of a bug causing the stage on the
        #Willamette set up to set its position to the inverse of the position set.      
        core.set_position(cls.Z_STAGE_NAME, z_pos)
        cls._logger.info(f"Stage z position set to {z_pos} um")


    @classmethod
    @handle_exception
    def get_x_position(cls) -> int:
        """
        Retrieves current X-position from stage and returns it
        """
        cls.wait_for_xy_stage()
        x_pos = int(core.get_x_position(cls.XY_STAGE_NAME))
        cls._logger.info(f"Current stage x position: {x_pos} um")
        return x_pos


    @classmethod
    @handle_exception
    def get_y_position(cls) -> int:
        """
        Retrieves current Y-position from stage and returns it
        """
        cls.wait_for_xy_stage()
        y_pos = int(core.get_y_position(cls.XY_STAGE_NAME))
        cls._logger.info(f"Current stage y position: {y_pos} um")
        return y_pos
    
    @classmethod
    @handle_exception
    def get_z_position(cls) -> int:
        """
        Retrieves current Y-position from stage and returns it
        """
        cls.wait_for_z_stage()
        z_pos = int(core.get_position(cls.Z_STAGE_NAME))
        cls._logger.info(f"Current stage z position: {z_pos} um")
        return z_pos

    @classmethod
    @handle_exception
    def reset_joystick(cls):
        """
        Sends commands to joystick to reset it to dsired state.

        The joystick tends to bug out after the SCAN command. This resets
        the joystick so that it works correctly. Essentially, "J X+ Y+ Z+" 
        re-enables the joystick axes, "J X=4 Y=3 Z=2" makes it so horizontal
        joystick movement moves the Z-axis and the knob moves the X-axis, and 
        "JSSPD Z=5" changes the speed of the joystick. 

        Please see the ASI MS-2000 documentation for more details on this command:

        http://www.asiimaging.com/downloads/manuals/Operations_and_Programming_Manual.pdf

        """
        cls.wait_for_xy_stage()
        cls.wait_for_z_stage()
        cls.send_serial_command_to_stage(cls._JOYSTICK_ENABLE)
        cls.send_serial_command_to_stage(cls._JOYSTICK_AXIS_RESET_COMMAND)
        cls.send_serial_command_to_stage(cls._JOYSTICK_Z_SPEED)
        cls._logger.info("Joystick has been reset")
        