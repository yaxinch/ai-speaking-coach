from datetime import datetime, timezone

from pydantic import BaseModel, field_validator


class UtcCreatedAtModel(BaseModel):
    """Serialize database timestamps as unambiguous UTC values."""

    @field_validator("created_at", mode="after", check_fields=False)
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
