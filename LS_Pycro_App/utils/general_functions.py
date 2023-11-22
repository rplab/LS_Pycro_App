from LS_Pycro_App.utils import constants


def frequency_to_exposure(frequency) -> float:
    return 1/frequency*constants.S_TO_MS


def exposure_to_frequency(exposure) -> float:
    return 1/(exposure*constants.MS_TO_S)


def value_in_range(value, bot, top):
    """
    returns value if bot < value < top, bot if value <= bot, and top if value => top.
    """
    return max(min(top, value), bot)


def float_to_str(value: float, num_decimals: int) -> str:
    """
    Converts given float to string with num_decimals decimal places.
    """
    return f"%.{num_decimals}f" % value


def swap_list_elements(lst, index_1, index_2):
    """
    Swaps elements located at index_1 and index_2 in lst.
    """
    lst[index_1], lst[index_2] = lst[index_2], lst[index_1]