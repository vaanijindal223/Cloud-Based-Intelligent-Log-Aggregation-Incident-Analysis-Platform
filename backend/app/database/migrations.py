"""Small, idempotent schema upgrades owned by the backend.

``Base.metadata.create_all()`` only creates tables that do not already exist.
This module covers additive changes to databases created by older releases, so a
Docker volume (including the production PostgreSQL volume) can be upgraded
without dropping incident or log data.
"""
from __future__ import annotations

import logging

from sqlalchemy import Engine, inspect, text

logger = logging.getLogger(__name__)

INCIDENT_MIGRATION_REVISION = "20260810_add_current_incident_columns"


def _incident_column_definitions(dialect: str) -> dict[str, str]:
    """Return every non-primary-key column required by the current model.

    Defaults make adding required fields safe for rows that already exist.  The
    SQLite variants keep the migration testable locally; production uses the
    PostgreSQL definitions.
    """
    timestamp = "DATETIME" if dialect == "sqlite" else "TIMESTAMP WITH TIME ZONE"
    now_default = "'1970-01-01 00:00:00+00:00'" if dialect == "sqlite" else "CURRENT_TIMESTAMP"
    return {
        "severity": "VARCHAR(20) NOT NULL DEFAULT 'MEDIUM'",
        "status": "VARCHAR(20) NOT NULL DEFAULT 'NEW'",
        "summary": "TEXT NOT NULL DEFAULT 'Incident awaiting correlation'",
        "start_time": f"{timestamp}",
        "end_time": f"{timestamp}",
        "affected_services": "TEXT NOT NULL DEFAULT '[]'",
        "root_cause": "TEXT",
        "confidence": "FLOAT",
        "created_at": f"{timestamp} NOT NULL DEFAULT {now_default}",
        "updated_at": f"{timestamp} NOT NULL DEFAULT {now_default}",
        "resolved_at": f"{timestamp}",
    }


def upgrade_database(engine: Engine) -> list[str]:
    """Upgrade an existing database to the current ``Incident`` table shape.

    This migration is deliberately additive: it never drops a table, column, or
    row. PostgreSQL's transaction-scoped advisory lock prevents two backend
    processes started by Docker/Uvicorn from applying the same ALTER concurrently.
    """
    with engine.begin() as connection:
        if connection.dialect.name == "postgresql":
            connection.execute(text("SELECT pg_advisory_xact_lock(20260810)"))

        if not inspect(connection).has_table("incidents"):
            # Fresh deployments are created by Base.metadata.create_all() before
            # this function is called.
            return []

        existing_columns = {
            column["name"] for column in inspect(connection).get_columns("incidents")
        }
        added: list[str] = []
        for name, definition in _incident_column_definitions(connection.dialect.name).items():
            if name not in existing_columns:
                connection.execute(text(f"ALTER TABLE incidents ADD COLUMN {name} {definition}"))
                added.append(name)

        # These are the indexes declared by Incident. create_all() does not add
        # indexes to a table that is already present.
        for index_name, column_name in (
            ("ix_incidents_severity", "severity"),
            ("ix_incidents_status", "status"),
            ("ix_incidents_start_time", "start_time"),
        ):
            connection.execute(text(
                f"CREATE INDEX IF NOT EXISTS {index_name} ON incidents ({column_name})"
            ))

        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                revision VARCHAR(100) PRIMARY KEY,
                applied_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        connection.execute(
            text("""
                INSERT INTO schema_migrations (revision, applied_at)
                VALUES (:revision, CURRENT_TIMESTAMP)
                ON CONFLICT (revision) DO NOTHING
            """),
            {"revision": INCIDENT_MIGRATION_REVISION},
        )

    if added:
        logger.info("Applied incident schema migration; added columns: %s", ", ".join(added))
    return added
