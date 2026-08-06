from dataclasses import dataclass

from app.simulation.models import LogStep


@dataclass(frozen=True)
class Failure:
    name: str
    description: str
    steps: list[LogStep]
