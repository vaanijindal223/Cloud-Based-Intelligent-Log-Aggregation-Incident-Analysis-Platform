from dataclasses import dataclass

from app.simulation.models import LogStep


@dataclass(frozen=True)
class Workflow:
    name: str
    description: str
    steps: list[LogStep]

    @property
    def duration(self) -> float:
        return max((s.offset_seconds for s in self.steps), default=0.0)
