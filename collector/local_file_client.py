"""Development-only adapter for the simulator's newline-delimited JSON log."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from collector.config import settings

logger = logging.getLogger(__name__)


def fetch_events(path: str | Path | None = None) -> list[dict]:
    """Wrap local JSON lines in the small envelope the normalizer accepts.

    Each line's exact-content hash is a stable, restart-safe source_event_id.
    The deliberately simple full scan is safe because PostgreSQL deduplicates
    it, including after a collector restart.
    """
    log_path = Path(path or settings.local_log_file)
    if not log_path.exists():
        logger.info("Local log file does not exist yet: %s", log_path)
        return []
    events: list[dict] = []
    try:
        with log_path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                message = line.strip()
                if not message:
                    continue
                digest = hashlib.sha256(message.encode("utf-8")).hexdigest()
                events.append({"eventId": f"local:{digest}", "message": message, "line": line_number})
    except OSError:
        logger.exception("Unable to read local log file %s", log_path)
        return []
    return events
