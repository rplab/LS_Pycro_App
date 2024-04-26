from LS_Pycro_App.controllers.select_controller import microscope, MicroscopeConfig
from LS_Pycro_App.utils.init_logger import init_logger
from LS_Pycro_App.utils.config import Config

init_logger()
if microscope == MicroscopeConfig.HTLS:
    user_config = Config(filename="HTLSConfig.cfg")
else:
    user_config = Config(filename="LSConfig.cfg")