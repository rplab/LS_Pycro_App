import serial


class Rotation():
    _COM_PORT = "COM16"
    _START = "/1"
    _END = "\n"
    _DEFAULT_SPEED = 50

    def __init__(self):
        self.com = serial.Serial(Rotation._COM_PORT, timeout=0.3)
        self.init()

    def init(self):
        self.set_speed(self._DEFAULT_SPEED)

    def get_position(self):
        self.write_command("?")
        return self.com.read()

    def set_speed(self, speed: float):
        self.write_command(f"v{speed}")

    def move_forward(self, num_steps: int):
        self.write_command(f"f{num_steps}")

    def move_backward(self, num_steps: int):
        self.write_command(f"f{num_steps}")

    def terminate(self):
        self.write_command("T")
                
    def close(self):
        self.com.close()

    def write_command(self, command: str):
        self.com.write(f"{self._START}{command}{self._END}".encode())
        