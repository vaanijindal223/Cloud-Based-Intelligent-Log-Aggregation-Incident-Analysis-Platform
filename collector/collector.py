import argparse
import logging
import time
from datetime import datetime, timedelta, timezone

from collector.cloudwatch_client import fetch_events
from collector.config import settings
from collector.db import get_last_checkpoint, insert_logs
from collector.local_file_client import fetch_events as fetch_local_events
from collector.normalizer import normalize_event

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run_once() -> int:
    source = settings.log_source.lower()
    if source == "local":
        raw_events = fetch_local_events()
        rows = [row for row in (normalize_event(e, source="local") for e in raw_events) if row is not None]
        checkpoint = None
    elif source == "cloudwatch":
        checkpoint = get_last_checkpoint("cloudwatch")
        if checkpoint is None:
            start_time = datetime.now(timezone.utc) - timedelta(seconds=settings.initial_lookback_seconds)
        else:
            start_time = checkpoint - timedelta(seconds=settings.overlap_seconds)
        raw_events = fetch_events(start_time=start_time)
        rows = [row for row in (normalize_event(e, source="cloudwatch") for e in raw_events) if row is not None]
    else:
        raise ValueError("LOG_SOURCE must be either 'local' or 'cloudwatch'")
    inserted = insert_logs(rows)
    logger.info(
        "Fetched %d %s events, inserted %d new rows (checkpoint=%s)",
        len(raw_events),
        source,
        inserted,
        checkpoint.isoformat() if checkpoint else "n/a",
    )
    return inserted


def run_forever() -> None:
    while True:
        try:
            run_once()
        except Exception:
            logger.exception("Collector poll failed; will retry next interval")
        time.sleep(settings.poll_interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Poll CloudWatch Logs and store normalized rows in PostgreSQL")
    parser.add_argument("--once", action="store_true", help="Run a single poll cycle and exit")
    args = parser.parse_args()

    if args.once:
        run_once()
    else:
        run_forever()


if __name__ == "__main__":
    main()
