from LS_Pycro_App.utils import dir_functions

class AcqDirectory(object):
    """
    Class to create and update directory for acquisition. As the acquisition progresses, fish, region, acq_type,
    and time_point are updated. Finally in the imaging sequences, get_directory() is called to get the updated
    directory as a string to be passed to a datastore.
    """
    FOLDER_NAME = "Acquisition"
    _FISH = "fish"
    _REGION = "pos"
    _ACQ_TYPE = "acq_type"
    _TIME_POINT = "timepoint"
        
    def __init__(self, directory: str):
        self.root = dir_functions.get_unique_directory(f"{directory}/{self.FOLDER_NAME}")

    def set_fish_num(self, fish_num: int):
        self._FISH = f"{self._FISH}{fish_num + 1}"

    def set_region_num(self, region_num: int):
        self._REGION = f"{self._REGION}{region_num + 1}"

    def set_acq_type(self, acq_type: str):
        self._ACQ_TYPE = acq_type

    def set_time_point(self, time_point: int):
        self._TIME_POINT = f"{self._TIME_POINT}{time_point + 1}"

    def set_root(self, new_root: str):
        self.root = dir_functions.get_unique_directory(f"{new_root}/{self.FOLDER_NAME}")

    def get_file_name(self):
        return f"{self._FISH}/{self._REGION}/{self._ACQ_TYPE}/{self._TIME_POINT}".replace("/", "_")

    def get_directory(self):
        return f"{self.root}/{self._FISH}/{self._REGION}/{self._ACQ_TYPE}/{self._TIME_POINT}/{self.get_file_name()}"
    