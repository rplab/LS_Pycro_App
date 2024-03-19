import os
import shutil
import time

import psutil

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


def move_files_to_parent(child_dir):
    try:
        for filename in os.listdir(child_dir):
            shutil.move(f"{child_dir}/{filename}", os.path.dirname(child_dir))
        os.rmdir(child_dir)
    except:
        pass


def is_disk_writing(dir: str):
    write_limit_mbps = 1
    write_time_s = 1
    start_used = psutil.disk_usage(dir).used
    time.sleep(write_time_s)
    mb_used = (psutil.disk_usage(dir).used - start_used)*constants.B_TO_MB
    mbps = mb_used/write_time_s
    return mbps > write_limit_mbps
 