from datetime import datetime

import boto3

from collector.config import settings


def _to_epoch_millis(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def fetch_events(start_time: datetime, end_time: datetime | None = None, client=None) -> list[dict]:
    """Fetch every CloudWatch log event in [start_time, end_time) from the configured
    log group, across all log streams, paginating through nextToken."""
    client = client or boto3.client("logs", region_name=settings.aws_region)
    kwargs = {
        "logGroupName": settings.log_group_name,
        "startTime": _to_epoch_millis(start_time),
        "interleaved": True,
    }
    if end_time is not None:
        kwargs["endTime"] = _to_epoch_millis(end_time)

    events: list[dict] = []
    next_token = None
    while True:
        if next_token:
            kwargs["nextToken"] = next_token
        response = client.filter_log_events(**kwargs)
        events.extend(response.get("events", []))
        next_token = response.get("nextToken")
        if not next_token:
            break
    return events
