import contextlib
from enum import Enum

import serial


class Port(Enum):
    O = "O"
    I = "I"
    E = "E"


class Pump():
    _COM_PORT = "COM4"
    _START = "/1"
    _END = "R\r"
    _DEFAULT_SPEED = 2
    _ACQ_VELOCITY = 4
    _FILL_VELOCITY = 100

    def __init__(self):
        self.com = serial.Serial(Pump._COM_PORT, timeout=0.3)

    def init(self):
        self.set_velocity(self._ACQ_VELOCITY)
        self.set_speed(self._DEFAULT_SPEED)

    def get_position(self):
        self.com.reset_output_buffer()
        self.write_command("?")
        return int((str(self.com.read(30)).split("`")[1].split("\\")[0]))

    def set_velocity(self, velocity: float):
        self.write_command(f"V{velocity}")

    def set_speed(self, speed: float):
        self.write_command(f"S{speed}")

    def set_max(self):
        self.write_command("A3000")

    def set_zero(self):
        self.write_command("A0")

    def terminate(self):
        self.write_command("T")

    def set_port(self, port: Port):
        """
        Accepted arguments are "E", "I", or "O".
        """
        with contextlib.suppress(KeyError):
            if isinstance(port, str):
                self.write_command(port)
            elif Port[port] in Port:
                self.write_command(port.value)
                
    def close(self):
        self.com.close()

    def write_command(self, command: str):
        self.com.write(f"{self._START}{command}{self._END}".encode())
