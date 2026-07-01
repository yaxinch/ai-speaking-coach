"""Persist question embeddings in SQLite."""

from alembic import op
import sqlalchemy as sa


revision = "0004_question_embeddings"
down_revision = "0003_question_bank"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("speaking_questions", sa.Column("embedding_vector", sa.LargeBinary(), nullable=True))
    op.add_column("speaking_questions", sa.Column("embedding_dimensions", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("speaking_questions", "embedding_dimensions")
    op.drop_column("speaking_questions", "embedding_vector")
