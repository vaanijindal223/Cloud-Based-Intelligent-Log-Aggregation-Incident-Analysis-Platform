import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Matches the Emitted log event contract (docs/data_contract.md, section 1), minus
# incident_id/failure_type which are legitimately absent on a healthy run.
REQUIRED_FIELDS = ["timestamp", "service", "severity", "message", "host", "trace_id", "workflow"]


def normalize_event(event: dict, *, source: str = "cloudwatch") -> dict | None:
    """Turn one raw CloudWatch log event into a Stored Log Record row
    (docs/data_contract.md, section 3). Returns None for events that can't be
    parsed or fail validation, so one bad line doesn't fail the whole batch."""
    try:
        payload = json.loads(event["message"])
    except (KeyError, TypeError, json.JSONDecodeError):
        logger.warning("Skipping unparseable %s event %s", source, event.get("eventId"))
        return None

    missing = [f for f in REQUIRED_FIELDS if f not in payload]
    if missing:
        logger.warning("Skipping %s event %s missing fields %s", source, event.get("eventId"), missing)
        return None

    try:
        timestamp = datetime.fromisoformat(payload["timestamp"])
    except (TypeError, ValueError):
        logger.warning("Skipping %s event %s with unparseable timestamp", source, event.get("eventId"))
        return None

    return {
        "timestamp": timestamp,
        "service": payload["service"],
        "severity": payload["severity"],
        "message": payload["message"],
        "host": payload["host"],
        "trace_id": payload["trace_id"],
        "incident_id": payload.get("incident_id"),
        "workflow": payload["workflow"],
        "failure_type": payload.get("failure_type"),
        "source": source,
        "source_event_id": event.get("eventId"),
        "processed": False,
    }
