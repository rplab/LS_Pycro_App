import serial


_COM_PORT = "COM15"
_START = "/1"
_END = "\n"
_DEFAULT_SPEED = 50

com = serial.Serial(_COM_PORT, timeout=0.3)

def init():
    set_speed(_DEFAULT_SPEED)

def get_position():
    write_command("?")
    return com.read()

def set_speed(speed: float):
    write_command(f"v{speed}")

def move_forward(num_steps: int):
    write_command(f"f{num_steps}")

def move_backward(num_steps: int):
    write_command(f"f{num_steps}")

def terminate():
    write_command("T")
            
def close():
    com.close()

def write_command(command: str):
    com.write(f"{_START}{command}{_END}".encode())
        