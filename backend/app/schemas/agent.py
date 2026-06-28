from typing import Literal

from pydantic import BaseModel, Field

PartType = Literal["part1", "part2", "part3"]


class CueCard(BaseModel):
    topic: str
    bullet_points: list[str] = Field(default_factory=list)
    preparation_instruction: str


class ExaminerQuestion(BaseModel):
    part_type: PartType
    question: str
    cue_card: CueCard | None = None


class GenerateQuestionRequest(BaseModel):
    part_type: PartType


class FeedbackResult(BaseModel):
    overall_band_score: float | None = None
    fluency_score: float | None = None
    vocabulary_score: float | None = None
    grammar_score: float | None = None
    pronunciation_note: str = "Not evaluated because this MVP uses text input only."
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    improved_answer: str = ""
    action_suggestions: list[str] = Field(default_factory=list)


class EvaluateAnswerRequest(BaseModel):
    part_type: PartType
    question: ExaminerQuestion
    user_answer: str = Field(min_length=1)


class EvaluateAnswerResponse(BaseModel):
    practice_id: str
    feedback: FeedbackResult
