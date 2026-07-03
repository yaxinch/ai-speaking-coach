from datetime import datetime

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.agent import ExaminerQuestion, FeedbackResult, PartType, QuestionDifficulty
from app.schemas.timestamps import UtcCreatedAtModel


class StartSectionPracticeRequest(BaseModel):
    part: PartType
    practiceGoal: str | None = Field(default=None, max_length=300)


class SectionCueCard(BaseModel):
    id: str
    topic: str
    prompt: str
    bulletPoints: list[str]
    preparationTimeSeconds: int = 60
    speakingTimeSeconds: int = 120
    source: str
    difficulty: QuestionDifficulty


class SectionPracticeItem(BaseModel):
    type: Literal["part1_question", "part2_cue_card", "part3_question"]
    id: str
    topic: str
    text: str
    source: str
    difficulty: QuestionDifficulty
    cueCard: SectionCueCard | None = None


class SectionPracticeMetadata(BaseModel):
    retrievalUsed: bool
    candidateCount: int
    selectorUsed: bool
    fallbackUsed: bool
    fallbackReason: str | None = None
    createdAt: datetime


class StartSectionPracticeResponse(BaseModel):
    selectionId: str
    mode: Literal["default", "goal_based"]
    practiceGoal: str | None
    part: PartType
    item: SectionPracticeItem
    metadata: SectionPracticeMetadata


class PracticeSummary(UtcCreatedAtModel):
    id: str
    part_type: PartType
    question_text: str
    overall_band: float | None
    created_at: datetime


class PracticeDetail(UtcCreatedAtModel):
    id: str
    part_type: PartType
    question: ExaminerQuestion
    question_text: str
    user_answer: str
    feedback: FeedbackResult
    overall_band: float | None
    created_at: datetime
    answer_source: str = "text"
    transcript_text: str | None = None
    audio_asset_id: str | None = None
    audio_url: str | None = None
