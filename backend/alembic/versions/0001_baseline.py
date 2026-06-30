"""Baseline text practice schema."""
from alembic import op
import sqlalchemy as sa

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "practice_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("part_type", sa.String(10), nullable=False),
        sa.Column("question_json", sa.Text(), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("user_answer", sa.Text(), nullable=False),
        sa.Column("feedback_json", sa.Text(), nullable=False),
        sa.Column("overall_band", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_practice_records_part_type", "practice_records", ["part_type"])
    op.create_index("ix_practice_records_created_at", "practice_records", ["created_at"])
    op.create_table(
        "mock_test_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("questions_json", sa.Text(), nullable=False),
        sa.Column("answers_json", sa.Text(), nullable=False),
        sa.Column("report_json", sa.Text(), nullable=False),
        sa.Column("overall_band", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_mock_test_records_created_at", "mock_test_records", ["created_at"])


def downgrade() -> None:
    op.drop_table("mock_test_records")
    op.drop_table("practice_records")
