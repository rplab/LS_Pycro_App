"""
This file contains the general wrapper used to handle exceptions from hardware devices.
"""

import inspect
import logging
from typing import Callable

from LS_Pycro_App.utils import acq_record
from LS_Pycro_App.utils.exceptions import HardwareException

#TODO Test hardware for raise exceptions and add specific exception handling from exceptions raised in
#methods themselves.
def handle_exception(funct: Callable):
    """
    Generic hardware exception handle. If failed, attempts funct one more time
    and then fails and raises HardwareException if it fails again.

    Every failure during an acquisition is also written to the acquisition record (utils/acq_record.py),
    once per failed call: "hardware_failure_recovered" if the retry succeeded, "hardware_failure" if it
    didn't. The record decides whether to stop a timelapse (consecutive timepoints with failures).
    """
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(inspect.getmodule(funct).__name__)
        attempts = 2
        first_error = None
        for exception_count in range(attempts):
            try:
                return_value = funct(*args, **kwargs)
            except Exception as e:
                first_error = first_error or e
                message = f"Exception raised during {funct.__name__}"
                if exception_count < attempts - 1:
                    message += ", reattempting"
                logger.exception(message)
            else:
                logger.info(f"{funct.__name__}() completed")
                if first_error is not None:
                    acq_record.report("hardware_failure_recovered", f"{funct.__name__}: {first_error!r}")
                return return_value
        
        message = f"{funct.__name__}() failed. Check device, logs, and MM Core logs"
        logger.info(message)
        print(message)
        acq_record.report("hardware_failure", f"{funct.__name__}: {first_error!r}")
        raise HardwareException(message)
    return wrapper
