from hardware.stage import Stage

class KlaStage(Stage):
    STAGE_SERIAL_LABEL = "TigerCommHub"
    X_AXIS_LABEL = "X"
    Y_AXIS_LABEL = "Y"
    Z_AXIS_LABEL = "Z"
    _INITIALIZE_SCAN_AXES = "2 SCAN Y=0 Z=0"
    _START_SCAN_COMMAND  = "2 SCAN"
    _SCANR_COMMAND_START = "2 SCANR"
    _JOYSTICK_AXIS_RESET_COMMAND = ""
    _JOYSTICK_Z_SPEED_COMMAND = "JSSPD Z=50"
 