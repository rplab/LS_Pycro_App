from hardware.stage import Stage

class Stage(Stage):
    def is_z_stage_first(current_x_pos, destination_x_pos):
        return current_x_pos > destination_x_pos

    STAGE_SERIAL_LABEL = "TigerCommHub"
    _X_AXIS_LABEL = "X"
    _Y_AXIS_LABEL = "Y"
    _Z_AXIS_LABEL = "Z"
    _INITIALIZE_SCAN_AXES = "2 SCAN Y=0 Z=9 F=0"
    _START_SCAN_COMMAND  = "2 SCAN"
    _SCANR_COMMAND_START = "2 SCANR"
    _SCANV_COMMAND = "2 SCANV Z=0"
    _JOYSTICK_AXIS_RESET_COMMAND = ""
    _JOYSTICK_Z_SPEED_COMMAND = "JSSPD Z=50"
 