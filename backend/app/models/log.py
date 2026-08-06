from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class Log(Base):
    """Stored Log Record — see docs/data_contract.md. This is the shape every
    downstream module (correlation engine, timeline, KB, LLM, dashboard) reads."""

    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    service: Mapped[str] = mapped_column(String(100), index=True)
    severity: Mapped[str] = mapped_column(String(20), index=True)
    message: Mapped[str] = mapped_column(Text)
    host: Mapped[str] = mapped_column(String(150))
    trace_id: Mapped[str] = mapped_column(String(100), index=True)
    incident_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    workflow: Mapped[str | None] = mapped_column(String(100), nullable=True)
    failure_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Collector-owned bookkeeping (docs/data_contract.md, section 3) — not part of the
    # emitted log event, set only when a row is written by the collector.
    source: Mapped[str] = mapped_column(String(50), default="cloudwatch")
    source_event_id: Mapped[str | None] = mapped_column(String(200), nullable=True, unique=True, index=True)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
