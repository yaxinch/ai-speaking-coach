from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SpeakingQuestion(Base):
    """A reviewed or reviewable IELTS Speaking practice question."""

    __tablename__ = "speaking_questions"
    __table_args__ = (
        CheckConstraint("part IN ('part1', 'part2', 'part3')", name="ck_speaking_questions_part"),
        CheckConstraint(
            "difficulty IS NULL OR difficulty IN ('easy', 'medium', 'hard')",
            name="ck_speaking_questions_difficulty",
        ),
        CheckConstraint(
            "source_type IN ('official_sample', 'education_site', 'recent_recalled', 'predicted', 'llm_generated')",
            name="ck_speaking_questions_source_type",
        ),
        CheckConstraint(
            "confidence IN ('high', 'medium_high', 'medium', 'low')",
            name="ck_speaking_questions_confidence",
        ),
        CheckConstraint(
            "status IN ('pending_review', 'approved', 'rejected')",
            name="ck_speaking_questions_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    part: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    cue_card_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    cue_card_bullets: Mapped[str | None] = mapped_column(Text, nullable=True)
    topic: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    sub_topic: Mapped[str | None] = mapped_column(String(120), nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    source_name: Mapped[str] = mapped_column(String(160), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_format: Mapped[str] = mapped_column(String(20), nullable=False, default="webpage")
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    season: Mapped[str | None] = mapped_column(String(40), nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending_review", index=True)
    embedding_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    embedding_vector_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    embedding_vector: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    embedding_dimensions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
