from dataclasses import dataclass


@dataclass
class ControllerState:
    lx: float = 0.0
    ly: float = 0.0
    rx: float = 0.0
    ry: float = 0.0
    dpad_x: int = 0
    dpad_y: int = 0
    lt: float = 0.0
    rt: float = 0.0


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))
