from hardware.stage import Stage

class WilStage(Stage):
    STAGE_SERIAL_LABEL = "ASI-XYStage"
    X_AXIS_LABEL = "Z"
    Y_AXIS_LABEL = "Y"
    Z_AXIS_LABEL = "X"
    _INITIALIZE_SCAN_AXES = "SCAN X=1 Y=0 Z=0"
    _START_SCAN_COMMAND  = "SCAN"
    _SCANR_COMMAND_START = "SCANR"
    _JOYSTICK_AXIS_RESET_COMMAND = "J X=4 Y=3 Z=2"
    _JOYSTICK_Z_SPEED_COMMAND = "JSSPD Z=50"
 