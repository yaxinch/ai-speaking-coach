from typing import Literal

from pydantic import BaseModel, Field

PartType = Literal["part1", "part2", "part3"]


class WeakPronunciationWord(BaseModel):
    word: str
    accuracy_score: float
    error_type: str | None = None


class PronunciationAssessment(BaseModel):
    available: bool = False
    provider: str = "disabled"
    is_mock: bool = False
    pron_score: float | None = None
    estimated_ielts_band: float | None = None
    accuracy_score: float | None = None
    fluency_score: float | None = None
    prosody_score: float | None = None
    weak_words: list[WeakPronunciationWord] = Field(default_factory=list)
    message: str = "Pronunciation assessment is not configured."


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
    pronunciation_score: float | None = None
    pronunciation_note: str = "Pronunciation cannot be evaluated accurately from a transcript alone."
    pronunciation_assessment: PronunciationAssessment | None = None
    summary: str = ""
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    corrections: list["Correction"] = Field(default_factory=list)
    improved_answer: str = ""
    action_suggestions: list[str] = Field(default_factory=list)
    next_practice_suggestion: str = ""


class Correction(BaseModel):
    original: str
    corrected: str
    reason: str


class EvaluateAnswerRequest(BaseModel):
    part_type: PartType
    question: ExaminerQuestion
    user_answer: str = Field(min_length=1)


class EvaluateAnswerResponse(BaseModel):
    practice_id: str
    feedback: FeedbackResult
