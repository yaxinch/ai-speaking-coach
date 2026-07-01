from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


Part = Literal["part1", "part2", "part3"]
Difficulty = Literal["easy", "medium", "hard"]
SourceType = Literal["official_sample", "education_site", "recent_recalled", "predicted", "llm_generated"]
Confidence = Literal["high", "medium_high", "medium", "low"]
ReviewStatus = Literal["pending_review", "approved", "rejected"]


class QuestionInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    part: Part
    question: str = Field(min_length=3, max_length=1000)
    cue_card_title: str | None = None
    cue_card_bullets: list[str] | None = None
    topic: str | None = None
    sub_topic: str | None = None
    difficulty: Difficulty | None = None
    source_name: str = Field(min_length=1, max_length=160)
    source_url: str = Field(min_length=1)
    source_type: SourceType
    source_format: Literal["webpage", "pdf", "manual"] = "webpage"
    confidence: Confidence
    season: str | None = None
    raw_text: str | None = None
    content_hash: str | None = None
    status: ReviewStatus = "pending_review"
    embedding_text: str | None = None
    embedding_model: str | None = None
    embedding_vector_id: str | None = None

    @field_validator("cue_card_bullets", mode="before")
    @classmethod
    def parse_bullets(cls, value):
        if value in (None, ""):
            return None
        if isinstance(value, str):
            import json

            parsed = json.loads(value)
            if not isinstance(parsed, list):
                raise ValueError("cue_card_bullets must be a JSON list")
            return parsed
        return value

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("source_url must be an absolute HTTP(S) URL")
        return value
