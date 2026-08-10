import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from collector.local_file_client import fetch_events  # noqa: E402
from collector.normalizer import normalize_event  # noqa: E402


def _line(trace_id: str = "trace-local") -> str:
    return json.dumps({
        "timestamp": "2026-08-06T17:16:35.568703+00:00",
        "service": "order-service", "severity": "ERROR", "message": "Database timeout",
        "host": "host-1", "trace_id": trace_id, "workflow": "ecommerce",
        "incident_id": "INC-1", "failure_type": "database_timeout",
    })


def test_local_events_have_stable_ids_and_normalize(tmp_path):
    path = tmp_path / "application.log"
    path.write_text(_line() + "\n", encoding="utf-8")

    first, restarted = fetch_events(path), fetch_events(path)

    assert first[0]["eventId"] == restarted[0]["eventId"]
    row = normalize_event(first[0], source="local")
    assert row is not None
    assert row["source"] == "local"
    assert row["source_event_id"].startswith("local:")


def test_local_reader_keeps_valid_lines_when_one_is_malformed(tmp_path):
    path = tmp_path / "application.log"
    path.write_text("not-json\n" + _line() + "\n", encoding="utf-8")

    rows = [normalize_event(event, source="local") for event in fetch_events(path)]

    assert rows[0] is None
    assert rows[1] is not None
