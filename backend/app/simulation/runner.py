from __future__ import annotations

import asyncio
import socket
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.simulation.logger import write_log_entry
from app.simulation.models import SPEED_MULTIPLIERS, LogStep, Speed

if TYPE_CHECKING:
    from app.simulation.manager import SimulationState


async def run_simulation(state: "SimulationState", steps: list[LogStep], speed: Speed) -> None:
    """Write one log line per step, pacing the delay between writes in real
    time so a running simulation is actually observable (and stoppable) rather
    than dumping every line at once."""
    host = socket.gethostname()
    multiplier = SPEED_MULTIPLIERS[speed]
    prev_offset = 0.0
    try:
        for step in steps:
            delay = (step.offset_seconds - prev_offset) * multiplier
            if delay > 0:
                await asyncio.sleep(delay)
            prev_offset = step.offset_seconds

            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": step.service,
                "severity": step.severity,
                "message": step.message,
                "host": host,
                "trace_id": state.trace_id,
                "incident_id": state.incident_id,
                "workflow": state.workflow_name,
                "failure": state.failure_name,
            }
            write_log_entry(entry)
            state.record_emitted(entry)
        state.mark_completed()
    except asyncio.CancelledError:
        state.mark_stopped()
        raise
