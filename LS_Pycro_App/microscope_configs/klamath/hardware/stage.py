from hardware.stage import Stage

class Stage(Stage):
    STAGE_SERIAL_LABEL = "TigerCommHub"
    _X_AXIS_LABEL = "X"
    _Y_AXIS_LABEL = "Y"
    _Z_AXIS_LABEL = "Z"
    _INITIALIZE_SCAN_AXES = "2 SCAN Y=0 Z=0"
    _START_SCAN_COMMAND  = "2 SCAN"
    _SCANR_COMMAND_START = "2 SCANR"
    _JOYSTICK_AXIS_RESET_COMMAND = ""
    _JOYSTICK_Z_SPEED_COMMAND = "JSSPD Z=50"
 