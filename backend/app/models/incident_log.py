from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class IncidentLog(Base):
    """Normalized, idempotent relationship between a correlated incident and a log."""
    __tablename__ = "incident_logs"
    __table_args__ = (UniqueConstraint("incident_id", "log_id", name="uq_incident_log"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.incident_id", ondelete="CASCADE"), index=True)
    log_id: Mapped[int] = mapped_column(ForeignKey("logs.id", ondelete="CASCADE"), index=True)
