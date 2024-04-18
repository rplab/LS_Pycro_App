import contextlib
import time
from enum import Enum

import serial

_COM_PORT = "COM4"
_START = "/1"
_END = "R\r"
_DEFAULT_SPEED = 2
_ACQ_VELOCITY = 4
_FILL_VELOCITY = 100
_MIN_POSITION = 300
_MAX_POSITION = 3000
_POSITION_WAIT_S = 0.1

com = serial.Serial(_COM_PORT, timeout=0.3)


class Port(Enum):
    O = "O"
    I = "I"
    E = "E"


def init():
    set_velocity(_ACQ_VELOCITY)
    set_speed(_DEFAULT_SPEED)
    set_port(Port.O)


def get_position():
    com.reset_output_buffer()
    _write_command("?")
    try:
        position = int((str(com.read(30)).split("`")[1].split("\\")[0]))
    except:
        get_position()
    return position


def fill():
    set_velocity(_FILL_VELOCITY)
    set_max()
    while get_position() < _MAX_POSITION:
        time.sleep(_POSITION_WAIT_S)
    terminate()


def empty():
    set_velocity(_FILL_VELOCITY)
    set_zero()
    while get_position() > _MIN_POSITION:
        time.sleep(_POSITION_WAIT_S)
    terminate()


def set_velocity(velocity: float):
    _write_command(f"V{velocity}")


def set_speed(speed: float):
    _write_command(f"S{speed}")


def set_max():
    _write_command("A3000")


def set_zero():
    _write_command("A0")


def terminate():
    _write_command("T")


def set_port(port: Port):
    """
    Accepted arguments are "E", "I", or "O".
    """
    with contextlib.suppress(KeyError):
        if isinstance(port, str):
            _write_command(port)
        elif Port[port] in Port:
            _write_command(port.value)
            

def close_com():
    com.close()


def _write_command(command: str):
    com.write(f"{_START}{command}{_END}".encode())
