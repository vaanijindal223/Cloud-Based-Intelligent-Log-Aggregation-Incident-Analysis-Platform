import asyncio
import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone

from app.simulation.failures import get_failure
from app.simulation.models import Speed
from app.simulation.runner import run_simulation
from app.simulation.workflows import get_workflow


class SimulationAlreadyRunning(Exception):
    pass


class NoRunningSimulation(Exception):
    pass


@dataclass
class SimulationState:
    workflow_name: str
    failure_name: str
    speed: Speed
    trace_id: str
    incident_id: str | None
    started_at: str
    total_steps: int
    emitted: list[dict] = field(default_factory=list)
    status: str = "running"  # running | completed | stopped

    def record_emitted(self, entry: dict) -> None:
        self.emitted.append(entry)

    def mark_completed(self) -> None:
        self.status = "completed"

    def mark_stopped(self) -> None:
        self.status = "stopped"

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "workflow": self.workflow_name,
            "failure": self.failure_name,
            "speed": self.speed.value,
            "trace_id": self.trace_id,
            "incident_id": self.incident_id,
            "started_at": self.started_at,
            "emitted_count": len(self.emitted),
            "total_steps": self.total_steps,
            "last_log": self.emitted[-1] if self.emitted else None,
        }


class SimulationManager:
    """Runs at most one simulation at a time. A demo app doesn't need concurrent
    incidents, and serializing them keeps /status and /stop unambiguous."""

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._state: SimulationState | None = None

    def status(self) -> dict:
        if self._state is None:
            return {"status": "idle"}
        return self._state.to_dict()

    def start(self, workflow_name: str, failure_name: str, speed: Speed) -> dict:
        if self._task is not None and not self._task.done():
            raise SimulationAlreadyRunning("A simulation is already running. Stop it first.")

        workflow = get_workflow(workflow_name)
        failure = get_failure(failure_name)

        steps = list(workflow.steps)
        if failure.steps:
            gap = 0.5
            offset_base = workflow.duration + gap
            steps += [replace(s, offset_seconds=offset_base + s.offset_seconds) for s in failure.steps]

        state = SimulationState(
            workflow_name=workflow.name,
            failure_name=failure.name,
            speed=speed,
            trace_id=uuid.uuid4().hex,
            incident_id=f"INC-{uuid.uuid4().hex[:8].upper()}" if failure.steps else None,
            started_at=datetime.now(timezone.utc).isoformat(),
            total_steps=len(steps),
        )
        self._state = state
        self._task = asyncio.create_task(run_simulation(state, steps, speed))
        return state.to_dict()

    def stop(self) -> dict:
        if self._task is None or self._task.done():
            raise NoRunningSimulation("No simulation is currently running.")
        self._task.cancel()
        assert self._state is not None
        return self._state.to_dict()


manager = SimulationManager()
