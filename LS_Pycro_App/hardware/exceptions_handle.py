"""
This file contains the general wrapper used to handle exceptions from hardware devices.
"""

import inspect
import logging
from typing import Callable

from LS_Pycro_App.utils.exceptions import HardwareException

#TODO Test hardware for raise exceptions and add specific exception handling from exceptions raised in
#methods themselves.
def handle_exception(funct: Callable):
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(inspect.getmodule(funct).__name__)
        
        attempts = 2
        for exception_count in range(attempts):
            try:
                return_value = funct(*args, **kwargs)
            except Exception:
                message = f"Exception raised during {funct.__name__}"
                if exception_count < attempts - 1:
                    message += ", reattempting"
                logger.exception(message)
            else:
                logger.info(f"{funct.__name__}() completed")
                return return_value
        
        message = f"{funct.__name__}() failed. Check device, logs, and MM Core logs"
        logger.info(message)
        print(message)
        raise HardwareException
    return wrapper
