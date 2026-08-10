from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.session import Base


class IncidentAlert(Base):
    __tablename__ = "incident_alerts"
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.incident_id", ondelete="CASCADE"), primary_key=True)
    sent: Mapped[bool] = mapped_column(Boolean, default=False)
    message_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

