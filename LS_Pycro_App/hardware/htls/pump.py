import contextlib
import time
from enum import Enum

import serial


class Port(Enum):
    O = "O"
    I = "I"
    E = "E"


_COM_PORT = "COM4"
_START = "/1"
_END = "R\r"
DEFAULT_SPEED = 2
DETECTION_VELOCITY = 4
FILL_VELOCITY = 100
MIN_POSITION = 300
MAX_POSITION = 2900
POSITION_WAIT_S = 0.1
FILL_PORT = Port.E
ACQ_PORT = Port.O


com = serial.Serial(_COM_PORT, timeout=0.3)
port = ACQ_PORT
speed = DEFAULT_SPEED
velocity = DETECTION_VELOCITY


def init():
    set_velocity(velocity)
    set_speed(speed)
    set_port(port)


def is_empty():
    return get_position() <= MIN_POSITION


def is_full():
    return get_position == MAX_POSITION


def fill_check():
    prev_port = port
    prev_velocity = velocity
    prev_speed = speed
    if is_empty:
        terminate()
        fill()
    set_port(prev_port)
    set_velocity(prev_velocity)
    set_speed(prev_speed)


def get_position():
    com.reset_output_buffer()
    _write_command("?")
    try:
        position = int((str(com.read(30)).split("`")[1].split("\\")[0]))
    except:
        get_position()
    return position


def fill():
    port = FILL_PORT
    velocity = FILL_VELOCITY
    set_port(port)
    set_velocity(velocity)
    set_max()
    while get_position() < MAX_POSITION:
        time.sleep(POSITION_WAIT_S)
    terminate()


def empty():
    set_port(FILL_PORT)
    set_velocity(FILL_VELOCITY)
    set_zero()
    while get_position() > MIN_POSITION:
        time.sleep(POSITION_WAIT_S)
    terminate()


def set_velocity(velocity: float):
    velocity = velocity
    _write_command(f"V{velocity}")


def set_speed(speed: float):
    speed = speed
    _write_command(f"S{speed}")


def set_max():
    _write_command("A3000")


def set_zero():
    _write_command("A0")


def terminate():
    _write_command("T")


def set_port(new_port: Port):
    """
    Accepted arguments are "E", "I", or "O".
    """
    global port
    with contextlib.suppress(KeyError):
        if isinstance(new_port, str):
            port = Port[port]
            _write_command(port)
        elif Port[port] in Port:
            port = port
            _write_command(port.value)
            

def close_com():
    com.close()


def _write_command(command: str):
    com.write(f"{_START}{command}{_END}".encode())
