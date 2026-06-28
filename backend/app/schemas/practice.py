from datetime import datetime

from pydantic import BaseModel

from app.schemas.agent import ExaminerQuestion, FeedbackResult, PartType


class PracticeSummary(BaseModel):
    id: str
    part_type: PartType
    question_text: str
    overall_band: float | None
    created_at: datetime


class PracticeDetail(BaseModel):
    id: str
    part_type: PartType
    question: ExaminerQuestion
    question_text: str
    user_answer: str
    feedback: FeedbackResult
    overall_band: float | None
    created_at: datetime
