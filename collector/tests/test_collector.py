import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import collector.collector as collector_mod  # noqa: E402

VALID_EVENT = {
    "eventId": "evt-1",
    "timestamp": 1699999999000,
    "message": (
        '{"timestamp": "2026-08-06T17:16:35.568703+00:00", "service": "order-service", '
        '"severity": "ERROR", "message": "Database retry failed", "host": "host-1", '
        '"trace_id": "trace-1", "incident_id": "INC-1", "workflow": "ecommerce", '
        '"failure_type": "database_timeout"}'
    ),
    "logStreamName": "stream-1",
}

BAD_EVENT = {"eventId": "evt-2", "timestamp": 1699999999000, "message": "not json", "logStreamName": "s"}


def test_run_once_normalizes_and_inserts():
    with patch.object(collector_mod, "get_last_checkpoint", return_value=None) as mock_checkpoint, \
         patch.object(collector_mod, "fetch_events", return_value=[VALID_EVENT]) as mock_fetch, \
         patch.object(collector_mod, "insert_logs", return_value=1) as mock_insert:
        inserted = collector_mod.run_once()

    assert inserted == 1
    mock_checkpoint.assert_called_once()
    mock_fetch.assert_called_once()
    rows = mock_insert.call_args[0][0]
    assert len(rows) == 1
    assert rows[0]["source_event_id"] == "evt-1"


def test_run_once_skips_unparseable_events():
    with patch.object(collector_mod, "get_last_checkpoint", return_value=None), \
         patch.object(collector_mod, "fetch_events", return_value=[BAD_EVENT]), \
         patch.object(collector_mod, "insert_logs", return_value=0) as mock_insert:
        inserted = collector_mod.run_once()

    assert inserted == 0
    assert mock_insert.call_args[0][0] == []


def test_run_once_uses_checkpoint_with_overlap():
    from datetime import datetime, timedelta, timezone

    checkpoint = datetime(2026, 8, 6, 12, 0, 0, tzinfo=timezone.utc)
    with patch.object(collector_mod, "get_last_checkpoint", return_value=checkpoint), \
         patch.object(collector_mod, "fetch_events", return_value=[]) as mock_fetch, \
         patch.object(collector_mod, "insert_logs", return_value=0):
        collector_mod.run_once()

    called_start_time = mock_fetch.call_args.kwargs["start_time"]
    assert called_start_time == checkpoint - timedelta(seconds=collector_mod.settings.overlap_seconds)
