from datetime import datetime

from pydantic import BaseModel


class LogEventIn(BaseModel):
    """Emitted log event — docs/data_contract.md, section 1.
    What the simulator writes to application.log and what CloudWatch's `message`
    field unwraps to."""

    timestamp: datetime
    service: str
    severity: str
    message: str
    host: str
    trace_id: str
    incident_id: str | None = None
    workflow: str
    failure_type: str | None = None


class LogRecordOut(LogEventIn):
    """Stored Log Record — docs/data_contract.md, section 3.
    Adds the collector-owned bookkeeping fields. This is the shape every
    downstream module (correlation engine, timeline, KB, LLM, dashboard) reads."""

    model_config = {"from_attributes": True}

    id: int
    source: str
    source_event_id: str | None = None
    processed: bool
