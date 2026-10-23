import logging
import os
import shutil
import time

from LS_Pycro_App.utils import constants
 
def get_unique_directory(dir: str) -> str:
    """
    returns save_path with "_i" appended where i is the first integar such that save_path is unique.
    """
    i = 1
    while os.path.isdir(dir):
        dir = dir.strip(f"_{i-1}") + f"_{i}"
        i += 1
    return dir


def is_enough_space(data_mb, required_percentage, dir: str) -> bool:
    """ 
    returns 
    """
    usage = shutil.disk_usage(dir)
    total_space = usage[0]
    used_space = usage[1] + data_mb*constants.MB_TO_B
    return used_space/total_space < required_percentage


_logger = logging.getLogger(__name__)
#Windows may briefly keep a just-closed file locked, so each move is retried a few times.
_MOVE_ATTEMPTS = 5
_MOVE_RETRY_DELAY_S = 0.5


def move_files_to_parent(child_dir) -> bool:
    """
    Moves files and directories in child_dir to parent directory and then deletes 
    child_dir.

    Each item is checked after moving (present in the parent, gone from child_dir). Nothing is ever
    overwritten: if an item of the same name already exists in the parent, it is left in child_dir.
    Failures are logged as errors (never silently ignored), and child_dir is only removed if it is
    empty. Returns True if everything was moved and child_dir removed.
    """
    parent_dir = os.path.dirname(child_dir)
    try:
        names = os.listdir(child_dir)
    except OSError:
        _logger.exception(f"Could not list {child_dir}; files not moved to {parent_dir}")
        return False
    failed = []
    for name in names:
        source = os.path.join(child_dir, name)
        destination = os.path.join(parent_dir, name)
        if os.path.exists(destination):
            _logger.error(f"Not moving {source}: {destination} already exists")
            failed.append(name)
            continue
        for attempt in range(_MOVE_ATTEMPTS):
            try:
                shutil.move(source, destination)
            except OSError:
                if attempt == _MOVE_ATTEMPTS - 1:
                    _logger.exception(f"Could not move {source} to {parent_dir}")
                else:
                    time.sleep(_MOVE_RETRY_DELAY_S)
            else:
                break
        if not os.path.exists(destination) or os.path.exists(source):
            _logger.error(f"Move of {source} to {parent_dir} not verified")
            failed.append(name)
    if failed:
        _logger.error(f"{len(failed)} item(s) left in {child_dir}: {failed}")
        return False
    try:
        os.rmdir(child_dir)
    except OSError:
        _logger.exception(f"Could not remove {child_dir} after moving its files")
        return False
    _logger.info(f"Moved {len(names)} item(s) from {child_dir} to {parent_dir}")
    return True
    