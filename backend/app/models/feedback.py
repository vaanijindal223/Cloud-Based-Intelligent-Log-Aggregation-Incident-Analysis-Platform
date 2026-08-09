from sqlalchemy import Boolean, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class Feedback(Base):
    __tablename__ = "feedback"

    incident_id: Mapped[int] = mapped_column(
        ForeignKey("incidents.incident_id", ondelete="CASCADE"), primary_key=True
    )
    ai_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    engineer_comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
