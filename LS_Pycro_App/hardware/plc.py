import logging
import numpy as np
from hardware.exceptions_handle import handle_exception
from utils import constants
from utils.abc_attributes_wrapper import abstractattributes
from utils.pycro import core

@abstractattributes
class Plc():
    #"abstract attributes" Interpreter will throw an error if the following aren't declared.
    _ADDR_CAM_OUT : int
    _ADDR_STAGE_TTL : int

    _logger = logging.getLogger(__name__)
    PLC_NAME = "PLogic:E:36"

    #PLC property names
    _POINTER_POSITION = "PointerPosition"
    _EDIT_CELL_TYPE = "EditCellCellType"
    _EDIT_CELL_CONFIG = "EditCellConfig"
    _EDIT_CELL_INPUT_1 = "EditCellInput1"
    _EDIT_CELL_INPUT_2 = "EditCellInput2"

    #PLC element values
    _VAL_INPUT = "0 - input"
    _VAL_CONSTANT = "0 - constant"
    _VAL_OUTPUT = "2 - output (push-pull)"
    _VAL_AND = "5 - 2-input AND"
    _VAL_OR = "6 - 2-input OR"
    _VAL_ONE_SHOT = "8 - one shot"
    _VAL_DELAY = "9 - delay"

    #PLC element addresses
    _ADDR_CLK = 192
    _ADDR_DELAY_1 = 1
    _ADDR_OR = 2
    _ADDR_AND = 3
    _ADDR_DELAY_2 = 4
    _ADDR_ONE_SHOT = 5
    _ADDR_CONSTANT = 6

    #PLC properties
    _CLOCK_TICKS_PER_MS = 4
    _TRIGGER_PULSE_WIDTH = 3*_CLOCK_TICKS_PER_MS
    _PLC_CONSTANT_STATE = 1


    #PLC commands
    @classmethod
    def wait_for_plc(cls):
        #core.wait_for_device(cls.PLC_NAME)
        pass

    @classmethod
    @handle_exception
    def init_pulse_mode(cls):
        """
        Initializes PLC circuit for use in z-stack acquisition and lsrm.

        The PLC (programmable logic card) is used to create logic circuits through software.
        There are a couple different ways to set up its elements. The method used in this program
        is the pointer system. Essentially, you set the pointer to the element you want to create/edit,
        set those properties, and then set the pointer to the next element.
        
        Please see the following for more information on how this works:

        http://www.asiimaging.com/downloads/manuals/Programmable_Logic_Card.pdf

        The circuit here creates a pulse matching the stage speed and step size during 
        a z-stack. This pulse is sent to the camera as an external trigger. If the stage
        scan speed is set to 30 um/s and the step size is 1 um, then the PLC output
        will pulse at 30 Hz. If the step size is 2 um, it will instead pulse at 15 Hz.

        Note that since the clock of the PLC runs at 4kHz, 1 ms is equal to 4 clock ticks,
        and so values in ms sent to the PLC must be multiplied by 4.

        For a full realization of this circuit, please see the developer's guide
        """
        #waiting for device is a common occurance just to make sure
        #device isn't busy with other tasks while setting properties
        cls.wait_for_plc()
        #The frame interval is just the interval between pulses, determined
        #by the step size and scan speed. The values passed here are just the default
        #step size and z_scan_speed (didn't want an unnecessary import)
        frame_interval = cls._get_frame_interval(step_size=1, z_scan_speed=30)
        
        cls._set_plc_cell(cls._ADDR_STAGE_TTL, cls._VAL_INPUT, 0, 0, 0)
        cls._set_plc_cell(cls._ADDR_DELAY_1, cls._VAL_DELAY, 0, cls._ADDR_STAGE_TTL, cls._ADDR_CLK)
        cls._set_plc_cell(cls._ADDR_OR, cls._VAL_OR, 0, cls._ADDR_DELAY_1, cls._ADDR_DELAY_2)
        cls._set_plc_cell(cls._ADDR_AND, cls._VAL_AND, 0, cls._ADDR_OR, cls._ADDR_STAGE_TTL)
        cls._set_plc_cell(cls._ADDR_DELAY_2, cls._VAL_DELAY, frame_interval*cls._CLOCK_TICKS_PER_MS, cls._ADDR_AND, cls._ADDR_CLK)
        cls._set_plc_cell(cls._ADDR_ONE_SHOT, cls._VAL_ONE_SHOT, cls._TRIGGER_PULSE_WIDTH, cls._ADDR_AND, cls._ADDR_CLK)
        cls._set_plc_cell(cls._ADDR_CAM_OUT, cls._VAL_OUTPUT, cls._ADDR_ONE_SHOT, 0, 0)

        cls._logger.info(f"PLC initialized with frame interval {frame_interval} ms")

    @classmethod
    @handle_exception
    def set_plc_for_z_stack(cls, step_size: int, stage_scan_speed: float):
        """
        Sets the frame interval of the PLC for use during z-stack acquisition. 
        
        This is intended to be used after initialize_plc_for_z_stack() to update the frame interval
        to match the current step size. All other propertes set in initialize_plc_for_z_stack() 
        will remain the same.

        ### Parameters:

        #### step_size : int
            z-stack step_size in um

        #### z_scan_speed
            z-stack scan speed in mm/s
        """
        cls.wait_for_plc()

        frame_interval = cls._get_frame_interval(step_size, stage_scan_speed)

        cls._set_plc_pointer_position(cls._ADDR_DELAY_1)
        cls._edit_plc_cell_input_1(cls._ADDR_STAGE_TTL)

        cls._set_plc_pointer_position(cls._ADDR_AND)
        cls._edit_plc_cell_input_2(cls._ADDR_STAGE_TTL)

        cls._set_plc_pointer_position(cls._ADDR_DELAY_2)
        cls._edit_plc_cell_config(frame_interval*cls._CLOCK_TICKS_PER_MS)

        cls._logger.info(f"PLC set for z-stack with frame interval of {frame_interval} ms")

    @classmethod
    @handle_exception
    def set_plc_for_continuous_lsrm(cls, framerate: int):
        """
        Initializes PLC circuit to send continuouse pulses at set intervals determined
        by the framerate prameter.

        On the Klamath light sheet, this is used for lightsheet readout mode when the stage
        isn't triggering the PLC, such as videos and snaps in lightsheet readout mode.

        ### Parameters:

        #### framerate : int
            framerate of lightsheet readout mode.
        """
        cls.wait_for_plc()
        frame_interval = cls._get_frame_interval_from_framerate(framerate)

        cls._set_plc_pointer_position(cls._ADDR_DELAY_1)
        cls._edit_plc_cell_input_1(cls._ADDR_CONSTANT)

        cls._set_plc_pointer_position(cls._ADDR_AND)
        cls._edit_plc_cell_input_2(cls._ADDR_CONSTANT)

        cls._set_plc_pointer_position(cls._ADDR_DELAY_2)
        cls._edit_plc_cell_config(frame_interval*cls._CLOCK_TICKS_PER_MS)
        
        cls._set_plc_pointer_position(cls._ADDR_CONSTANT)
        cls._edit_plc_cell_type(cls._VAL_CONSTANT)
        cls._edit_plc_cell_config(cls._PLC_CONSTANT_STATE)

        cls._logger.info(f"PLC set for continuous LSRM with frame interval of {frame_interval} ms")

    #PLC helpers
    @classmethod
    def _set_plc_cell(cls, address, cell_type, config_value, input_1, input_2):
        """
        Sets PLC cell at given address with given properties
        """
        cls._set_plc_pointer_position(address)
        cls._edit_plc_cell_type(cell_type)
        cls._edit_plc_cell_config(config_value)
        cls._edit_plc_cell_input_1(input_1)
        cls._edit_plc_cell_input_2(input_2)

    @classmethod
    def _set_plc_pointer_position(cls, address):
        """
        Sets pointer position to address. Allows editing of element at address (or creation if it doesn't exist).
        """
        core.set_property(cls.PLC_NAME, cls._POINTER_POSITION, address)

    @classmethod
    def _edit_plc_cell_type(cls, type):
        """
        Edit cell type of element at current pointer position. Cell type is the type of logic gate, i.e. OR, AND, 
        ONESHOT, DELAY, etc.
        """
        core.set_property(cls.PLC_NAME, cls._EDIT_CELL_TYPE, type)

    @classmethod
    def _edit_plc_cell_config(cls, value):
        """
        Edit cell config of element at current pointer position. Generally, config is the most important value
        for configuring an element.
        """
        core.set_property(cls.PLC_NAME, cls._EDIT_CELL_CONFIG, value)

    @classmethod
    def _edit_plc_cell_input_1(cls, value):
        """
        Edit input_1 element at current pointer position. What this actually changes depends on the gate type.
        """
        core.set_property(cls.PLC_NAME, cls._EDIT_CELL_INPUT_1, value)

    @classmethod
    def _edit_plc_cell_input_2(cls, value):
        """
        Edit input_2 element at current pointer position. What this actually changes depends on the gate type.
        """
        core.set_property(cls.PLC_NAME, cls._EDIT_CELL_INPUT_2, value)

    @classmethod
    def _get_frame_interval(cls, step_size: int, z_scan_speed) -> int:
        """
        Calculates frame_interval from step_size and z_scan_speed and returns it.
        """
        #ceil is so the interval is greater than the framerate set in lsrm, which makes it so that 
        #pulses aren't missed by the camera.
        return np.ceil((step_size/(z_scan_speed*constants.UM_TO_MM))*cls._CLOCK_TICKS_PER_MS)/cls._CLOCK_TICKS_PER_MS

    @classmethod
    def _get_frame_interval_from_framerate(cls, framerate):
        """
        Really similar to globals.framerate_to_exposure(), except uses np.ceil instead of floor.
        """
        return np.ceil((1/framerate*constants.S_TO_MS)*cls._CLOCK_TICKS_PER_MS)/cls._CLOCK_TICKS_PER_MS

    @classmethod
    def get_true_z_stack_stage_speed(cls, z_scan_speed):
        return round(1/(cls._get_frame_interval(1, z_scan_speed))*constants.MM_TO_UM, 3)