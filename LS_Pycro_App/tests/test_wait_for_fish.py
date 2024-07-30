from LS_Pycro_App.models.acq_settings import HTLSSettings
from LS_Pycro_App.acquisition.acq_gui import HTLSAcqGui
from LS_Pycro_App.acquisition.sequences import HTLSSequence
from LS_Pycro_App.utils.exceptions import AbortFlag
from LS_Pycro_App.models.acq_directory import AcqDirectory
import time
from LS_Pycro_App.hardware.camera import Hamamatsu as Camera
from LS_Pycro_App.utils import pycro
from LS_Pycro_App.utils.pycro import core
import numpy as np
from LS_Pycro_App.utils import exceptions
from LS_Pycro_App.hardware import valves as Valves
from LS_Pycro_App.hardware import pump as Pump
import unittest


class TestWaitForFish(unittest.TestCase):
    def test_wait_for_fish(time_no_fish_s=0):
            Valves.open()
            Camera.set_binning(Camera.DETECTION_BINNING)
            Camera.set_exposure(Camera.DETECTION_EXPOSURE)
            pycro.set_channel(pycro.BF_CHANNEL)
            Camera.snap_image()
            bf_image = pycro.pop_next_image().get_raw_pixels()
            std_detect = np.std(bf_image)
            mean_detect = np.mean(bf_image)
            #initialize camera to detection settings
            Camera.set_binning(Camera.DETECTION_BINNING)
            Camera.set_exposure(Camera.DETECTION_EXPOSURE)
            pycro.set_channel(pycro.BF_CHANNEL)
            #begins the pumping of the fish
            core.stop_sequence_acquisition()
            core.start_continuous_sequence_acquisition(0)
            start_time = time.time()
            while True:
                total_time_s = time_no_fish_s + time.time() - start_time
                if core.get_remaining_image_count() > 0:
                    mm_image = pycro.pop_next_image()
                    image = mm_image.get_raw_pixels()
                    if np.std(image) > 1.1*std_detect and np.mean(image) < 0.8*mean_detect:
                        data = pycro.MultipageDatastore(fr"E:\HTLS Test\fish detection")
                        data.put_image(mm_image)
                        data.close()
                        break
                    elif total_time_s > HTLSSequence._DETECT_TIMEOUT_S:
                        raise exceptions.DetectionTimeoutException
                    #clear buffer so that it doesn't fill. We're just analyzing the newest image
                    #received so we don't need to be storing the images.
                    core.clear_circular_buffer()
                else:
                    core.sleep(0.5)
            core.stop_sequence_acquisition()
            #Valves closing first here is important because it instantly stops the fish.
            Valves.close()
            Pump.terminate()
            time.sleep(HTLSSequence._FISH_SETTLE_PAUSE_S)
            return total_time_s