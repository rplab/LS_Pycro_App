from LS_Pycro_App.utils import dir_functions

class AcqDirectory(object):
    """
    Class to create and update directory for acquisition. As the acquisition progresses, fish, region, acq_type,
    and time_point are updated. Finally, in the imaging sequences, get_directory() is called to get the updated
    directory as a string to be passed to a datastore.
    """
    FOLDER_NAME = "Acquisition"
    _FISH = "fish"
    _REGION = "pos"
    _ACQ_TYPE = "acq_type"
    _TIME_POINT = "timepoint"
        
    def __init__(self, directory: str):
        self.root = dir_functions.get_unique_directory(f"{directory}/{self.FOLDER_NAME}")
        self._fish = "fish1"
        self._region = "pos1"
        self._acq_type = "acq_type"
        self._time_point = "timepoint1"

    def set_fish_num(self, fish_num: int):
        self._fish = f"{self._FISH}{fish_num + 1}"

    def set_region_num(self, region_num: int):
        self._region = f"{self._REGION}{region_num + 1}"

    def set_acq_type(self, acq_type: str):
        self._acq_type = acq_type

    def set_time_point(self, time_point: int):
        self._time_point = f"{self._TIME_POINT}{time_point + 1}"

    def set_root(self, new_root: str):
        self.root = dir_functions.get_unique_directory(f"{new_root}/{self.FOLDER_NAME}")

    def get_file_name(self) -> str:
        return f"{self._fish}/{self._region}/{self._acq_type}/{self._time_point}".replace("/", "_")

    def get_directory(self) -> str:
        return f"{self.root}/{self._fish}/{self._region}/{self._acq_type}/{self._time_point}/{self.get_file_name()}"
    