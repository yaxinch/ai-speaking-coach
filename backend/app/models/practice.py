from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PracticeRecord(Base):
    __tablename__ = "practice_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    part_type: Mapped[str] = mapped_column(String(10), index=True)
    question_json: Mapped[str] = mapped_column(Text)
    question_text: Mapped[str] = mapped_column(Text)
    user_answer: Mapped[str] = mapped_column(Text)
    feedback_json: Mapped[str] = mapped_column(Text)
    overall_band: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
