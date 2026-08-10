from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert

from collector.config import settings

metadata = MetaData()

# Mirrors backend/app/models/log.py — the Stored Log Record shape (docs/data_contract.md,
# section 3). The collector never creates or migrates this table; the backend owns the
# schema, the collector only inserts into it.
logs_table = Table(
    "logs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("timestamp", DateTime(timezone=True)),
    Column("service", String(100)),
    Column("severity", String(20)),
    Column("message", Text),
    Column("host", String(150)),
    Column("trace_id", String(100)),
    Column("incident_id", String(100), nullable=True),
    Column("workflow", String(100), nullable=True),
    Column("failure_type", String(100), nullable=True),
    Column("source", String(50)),
    Column("source_event_id", String(200), unique=True, nullable=True),
    Column("processed", Boolean),
)

engine = create_engine(settings.database_url, pool_pre_ping=True)


def get_last_checkpoint(source: str = "cloudwatch") -> datetime | None:
    """Latest timestamp already stored from CloudWatch. Deriving the checkpoint from
    the table itself (instead of a separate pointer) means a collector restart can't
    desync from what's actually been persisted."""
    with engine.connect() as conn:
        return conn.execute(
            select(func.max(logs_table.c.timestamp)).where(logs_table.c.source == source)
        ).scalar()


def insert_logs(rows: list[dict]) -> int:
    """Insert normalized rows, silently skipping ones whose source_event_id already
    exists. Returns the number of rows actually inserted."""
    if not rows:
        return 0
    stmt = pg_insert(logs_table).values(rows).on_conflict_do_nothing(index_elements=["source_event_id"])
    with engine.begin() as conn:
        result = conn.execute(stmt)
        return result.rowcount
