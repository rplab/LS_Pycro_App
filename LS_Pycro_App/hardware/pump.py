import contextlib
import time
from enum import Enum

import serial


class Port(Enum):
    O = "O"
    I = "I"
    E = "E"


_COM_PORT = "COM5"
_START = "/1"
_END = "R\r"
DEFAULT_SPEED = 2
DETECTION_VELOCITY = 4
FILL_VELOCITY = 200

MIN_POSITION = 300
MAX_POSITION = 2900
POSITION_WAIT_S = 0.1
FILL_PORT = Port.E
ACQ_PORT = Port.O


def init():
    global port, speed, velocity, com
    port = FILL_PORT
    speed = DEFAULT_SPEED
    velocity = DETECTION_VELOCITY
    com = serial.Serial(_COM_PORT, timeout=0.05)
    set_speed(speed)
    set_velocity(velocity)
    set_port(port)


def is_empty():
    return get_position() <= MIN_POSITION


def is_full():
    return get_position == MAX_POSITION


def get_position():
    position = None
    while position is None:
        com.reset_output_buffer()
        _write_command("?")
        #? command returns a bunch of characters in addition to the position.
        #This grabs the position from the string of characters.
        try:
            position = int((str(com.read(30)).split("`")[1].split("\\")[0]))
            return position
        except (IndexError, ValueError):
            continue


def fill():
    port = FILL_PORT
    velocity = FILL_VELOCITY
    set_port(port)
    set_velocity(velocity)
    while get_position() < MAX_POSITION:
        set_max()
        time.sleep(POSITION_WAIT_S)
        terminate()
    terminate()


def empty():
    set_port(FILL_PORT)
    set_velocity(FILL_VELOCITY)
    while get_position() > MIN_POSITION:
        set_zero()
        time.sleep(POSITION_WAIT_S)
        terminate()
    terminate()


def set_velocity(velocity: int):
    velocity = velocity
    _write_command(f"V{velocity}")


def set_speed(speed: int):
    speed = speed
    _write_command(f"S{speed}")


def set_max():
    _write_command("A3000")


def set_zero():
    _write_command("A0")


def terminate():
    _write_command("T")


def set_port(new_port: Port | str):
    """
    Accepted arguments are "E", "I", or "O".
    """
    global port
    terminate()
    with contextlib.suppress(KeyError):
        if isinstance(new_port, str):
            port = Port[new_port]
            _write_command(port.name)
        elif new_port in Port:
            port = new_port
            _write_command(port.name)
            

def close_com():
    com.close()


def _write_command(command: str):
    com.write(f"{_START}{command}{_END}".encode())
    time.sleep(0.2)


def z_init():
    _write_command("Z1")
