"""Add persistent voice assets and targeted voice metadata."""
from alembic import op
import sqlalchemy as sa

revision = "0002_voice"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audio_assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("storage_name", sa.String(100), nullable=False, unique=True),
        sa.Column("mime_type", sa.String(80), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("question_id", sa.String(120), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("owner_type", sa.String(30), nullable=True),
        sa.Column("owner_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("question_id", "status", "owner_type", "owner_id", "created_at"):
        op.create_index(f"ix_audio_assets_{column}", "audio_assets", [column])
    op.add_column("practice_records", sa.Column("answer_source", sa.String(10), nullable=False, server_default="text"))
    op.add_column("practice_records", sa.Column("transcript_text", sa.Text(), nullable=True))
    op.add_column("practice_records", sa.Column("audio_asset_id", sa.String(36), nullable=True))
    op.create_index("ix_practice_records_audio_asset_id", "practice_records", ["audio_asset_id"])


def downgrade() -> None:
    op.drop_index("ix_practice_records_audio_asset_id", table_name="practice_records")
    op.drop_column("practice_records", "audio_asset_id")
    op.drop_column("practice_records", "transcript_text")
    op.drop_column("practice_records", "answer_source")
    op.drop_table("audio_assets")
