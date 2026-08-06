from dataclasses import dataclass
from enum import Enum


class Speed(str, Enum):
    INSTANT = "instant"
    FAST = "fast"
    NORMAL = "normal"


# Seconds of real delay per abstract "offset second" declared on a LogStep.
SPEED_MULTIPLIERS: dict[Speed, float] = {
    Speed.INSTANT: 0.0,
    Speed.FAST: 0.15,
    Speed.NORMAL: 1.0,
}


@dataclass(frozen=True)
class LogStep:
    offset_seconds: float
    service: str
    severity: str
    message: str
