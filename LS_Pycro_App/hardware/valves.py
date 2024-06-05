import serial

_COM_PORT = "COM16"
_END = "\n"


def init():
    global com, are_open
    com = serial.Serial(_COM_PORT, timeout=0.3)
    are_open = True
    open()
    pass


def close():
    global are_open
    are_open = False
    write_command("o")


def open():
    global are_open
    are_open = True
    write_command("c")


def get_status():
    global are_open
    return are_open


def write_command(command: str):
    com.write(f"{command}{_END}".encode())
