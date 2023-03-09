import os
import shutil
from utils import constants
 
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
    os.rename