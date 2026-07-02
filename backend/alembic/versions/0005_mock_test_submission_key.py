"""Add an idempotency key to full mock test records."""

from alembic import op
import sqlalchemy as sa


revision = "0005_mock_test_submission_key"
down_revision = "0004_question_embeddings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("mock_test_records", sa.Column("submission_key", sa.String(120), nullable=True))
    op.create_index(
        "ix_mock_test_records_submission_key",
        "mock_test_records",
        ["submission_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_mock_test_records_submission_key", table_name="mock_test_records")
    op.drop_column("mock_test_records", "submission_key")
