import unittest
from LS_Pycro_App.hardware.stage import KlaStage as Stage
from LS_Pycro_App.hardware.camera import Hamamatsu as Camera
from LS_Pycro_App.utils.fish_detection import get_region_1_x_offset

class TestHTLSOffset(unittest.TestCase):
    def test_offset(self):
        Camera.set_binning(2)
        Camera.set_exposure(10)
        x_pos = Stage.get_x_position()
        y_pos = Stage.get_y_position()
        z_pos = Stage.get_z_position()
        new_x = x_pos+get_region_1_x_offset((x_pos, y_pos, z_pos), (x_pos + 10000, y_pos, z_pos), x_step_size=200, fish_num=0)
        Stage.set_x_position(new_x)
        print(f"old x: {x_pos}")
        print(f"new x: {new_x}")

if __name__ == '__main__':
    unittest.main()