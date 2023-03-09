from utils import constants

def z_stack_speed_to_exposure(stage_speed) -> float:
    return 1/stage_speed*constants.S_TO_MS


def framerate_to_exposure(framerate) -> float:
    return 1/framerate*constants.S_TO_MS


def exposure_to_framerate(exposure) -> float:
    return 1/(exposure*constants.MS_TO_S)


def value_in_range(value, bot, top):
    """
    returns value if bot < value < top, bot if value <= bot, and top if value => top.
    """
    return max(min(top, value), bot)


def get_str_from_float(value: float, num_decimals: int) -> str:
    return f"%.{num_decimals}f" % value


def swap_list_elements(lst, index_1, index_2):
    lst[index_1], lst[index_2] = lst[index_2], lst[index_1]