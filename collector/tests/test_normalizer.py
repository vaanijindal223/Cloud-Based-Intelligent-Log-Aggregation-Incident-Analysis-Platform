import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from collector.normalizer import normalize_event  # noqa: E402

VALID_PAYLOAD = (
    '{"timestamp": "2026-08-06T17:16:35.568703+00:00", "service": "order-service", '
    '"severity": "ERROR", "message": "Database retry failed", "host": "host-1", '
    '"trace_id": "trace-1", "incident_id": "INC-1", "workflow": "ecommerce", '
    '"failure_type": "database_timeout"}'
)

HEALTHY_PAYLOAD = (
    '{"timestamp": "2026-08-06T17:16:35.568703+00:00", "service": "auth-service", '
    '"severity": "INFO", "message": "User login successful", "host": "host-1", '
    '"trace_id": "trace-2", "workflow": "ecommerce"}'
)


def _event(message: str, event_id: str = "evt-1") -> dict:
    return {"eventId": event_id, "timestamp": 1699999999000, "message": message, "logStreamName": "stream-1"}


def test_normalize_valid_event():
    row = normalize_event(_event(VALID_PAYLOAD))
    assert row is not None
    assert row["service"] == "order-service"
    assert row["source"] == "cloudwatch"
    assert row["source_event_id"] == "evt-1"
    assert row["processed"] is False
    assert row["incident_id"] == "INC-1"
    assert row["failure_type"] == "database_timeout"


def test_normalize_healthy_run_has_null_incident_fields():
    row = normalize_event(_event(HEALTHY_PAYLOAD))
    assert row is not None
    assert row["incident_id"] is None
    assert row["failure_type"] is None


def test_normalize_skips_invalid_json():
    assert normalize_event(_event("not json")) is None


def test_normalize_skips_missing_required_field():
    payload = '{"timestamp": "2026-08-06T17:16:35.568703+00:00", "service": "auth-service"}'
    assert normalize_event(_event(payload)) is None


def test_normalize_skips_unparseable_timestamp():
    payload = VALID_PAYLOAD.replace("2026-08-06T17:16:35.568703+00:00", "not-a-timestamp")
    assert normalize_event(_event(payload)) is None
