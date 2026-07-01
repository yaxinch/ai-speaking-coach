"""Add the reviewed IELTS Speaking practice question bank."""
from alembic import op
import sqlalchemy as sa


revision = "0003_question_bank"
down_revision = "0002_voice"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "speaking_questions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("part", sa.String(10), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("cue_card_title", sa.Text(), nullable=True),
        sa.Column("cue_card_bullets", sa.Text(), nullable=True),
        sa.Column("topic", sa.String(80), nullable=True),
        sa.Column("sub_topic", sa.String(120), nullable=True),
        sa.Column("difficulty", sa.String(10), nullable=True),
        sa.Column("source_name", sa.String(160), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("source_format", sa.String(20), nullable=False, server_default="webpage"),
        sa.Column("confidence", sa.String(20), nullable=False),
        sa.Column("season", sa.String(40), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending_review"),
        sa.Column("embedding_text", sa.Text(), nullable=True),
        sa.Column("embedding_model", sa.String(120), nullable=True),
        sa.Column("embedding_vector_id", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("part IN ('part1', 'part2', 'part3')", name="ck_speaking_questions_part"),
        sa.CheckConstraint(
            "difficulty IS NULL OR difficulty IN ('easy', 'medium', 'hard')", name="ck_speaking_questions_difficulty"
        ),
        sa.CheckConstraint(
            "source_type IN ('official_sample', 'education_site', 'recent_recalled', 'predicted', 'llm_generated')",
            name="ck_speaking_questions_source_type",
        ),
        sa.CheckConstraint(
            "confidence IN ('high', 'medium_high', 'medium', 'low')", name="ck_speaking_questions_confidence"
        ),
        sa.CheckConstraint(
            "status IN ('pending_review', 'approved', 'rejected')", name="ck_speaking_questions_status"
        ),
    )
    op.create_index("ux_speaking_questions_content_hash", "speaking_questions", ["content_hash"], unique=True)
    for column in ("status", "part", "topic", "difficulty", "confidence"):
        op.create_index(f"ix_speaking_questions_{column}", "speaking_questions", [column])


def downgrade() -> None:
    op.drop_table("speaking_questions")
