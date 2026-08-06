import json
from pathlib import Path

from app.config import settings


def write_log_entry(entry: dict, log_file: Path | None = None) -> None:
    """Append one structured log entry as a JSON line, in the shape the
    CloudWatch Agent will tail unchanged in Phase 3."""
    path = log_file or Path(settings.log_file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
