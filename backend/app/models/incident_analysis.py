from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.session import Base


class IncidentAnalysis(Base):
    __tablename__ = "incident_analyses"
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.incident_id", ondelete="CASCADE"), primary_key=True)
    summary: Mapped[str] = mapped_column(Text)
    probable_root_cause: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str] = mapped_column(Text, default="[]")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    suggested_resolution: Mapped[str] = mapped_column(Text)
    alternative_causes: Mapped[str] = mapped_column(Text, default="[]")
    historical_matches: Mapped[str] = mapped_column(Text, default="[]")
    model: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

