from datetime import datetime

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.agent import CueCard, PartType
from app.schemas.speaking import VoiceFeedback, VoiceScore


LEGACY_PART_COUNTS: dict[PartType, int] = {"part1": 4, "part2": 1, "part3": 3}
BANK_PART_COUNTS: dict[PartType, int] = {"part1": 6, "part2": 1, "part3": 4}
SUPPORTED_PART_COUNTS = (LEGACY_PART_COUNTS, BANK_PART_COUNTS)


class MockQuestion(BaseModel):
    part_type: PartType
    question_index: int = Field(ge=1)
    question: str
    cue_card: CueCard | None = None
    bank_question_id: str | None = None
    topic: str | None = None
    source: str | None = None
    difficulty: Literal["easy", "medium", "hard", "unknown"] | None = None


def validate_question_set(questions: list[MockQuestion]) -> list[MockQuestion]:
    counts = {part_type: sum(item.part_type == part_type for item in questions) for part_type in LEGACY_PART_COUNTS}
    if counts not in SUPPORTED_PART_COUNTS:
        raise ValueError("A full mock test must use either the legacy 4/1/3 or question-bank 6/1/4 profile.")
    for part_type, count in counts.items():
        part_questions = [question for question in questions if question.part_type == part_type]
        if len(part_questions) != count:
            raise ValueError(f"{part_type} must contain exactly {count} questions.")
        if sorted(question.question_index for question in part_questions) != list(range(1, count + 1)):
            raise ValueError(f"{part_type} question indexes must be sequential.")
    return questions


class GenerateMockTestResponse(BaseModel):
    questions: list[MockQuestion]

    @model_validator(mode="after")
    def validate_questions(self):
        validate_question_set(self.questions)
        return self


class MockAnswer(BaseModel):
    part_type: PartType
    question_index: int = Field(ge=1)
    question: MockQuestion
    answer_text: str = Field(min_length=1)
    audio_url: str | None = None
    audio_asset_id: str | None = None
    transcript_text: str | None = None
    voice_score: VoiceScore | None = None
    voice_feedback: VoiceFeedback | None = None


class QuestionAnalysis(BaseModel):
    question_index: int = Field(ge=1)
    band_estimate: float | None = None
    feedback: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    improved_answer: str = ""


class PartFeedback(BaseModel):
    band_estimate: float | None = None
    summary: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    question_analyses: list[QuestionAnalysis]


class MockTestReport(BaseModel):
    overall_band_score: float | None = None
    key_strengths: list[str] = Field(default_factory=list)
    key_weaknesses: list[str] = Field(default_factory=list)
    action_plan: list[str] = Field(default_factory=list)
    part1_feedback: PartFeedback
    part2_feedback: PartFeedback
    part3_feedback: PartFeedback

class EvaluateMockTestRequest(BaseModel):
    answers: list[MockAnswer]

    @model_validator(mode="after")
    def validate_answers(self):
        questions = [answer.question for answer in self.answers]
        validate_question_set(questions)
        for answer in self.answers:
            if not answer.answer_text.strip():
                raise ValueError("Every mock test answer must contain text.")
            if answer.part_type != answer.question.part_type or answer.question_index != answer.question.question_index:
                raise ValueError("Answer metadata must match its question.")
        return self


def validate_report_for_questions(report: MockTestReport, questions: list[MockQuestion]) -> None:
    counts = {part_type: sum(item.part_type == part_type for item in questions) for part_type in LEGACY_PART_COUNTS}
    feedback_by_part = {
        "part1": report.part1_feedback,
        "part2": report.part2_feedback,
        "part3": report.part3_feedback,
    }
    for part_type, count in counts.items():
        analyses = feedback_by_part[part_type].question_analyses
        if len(analyses) != count or sorted(item.question_index for item in analyses) != list(range(1, count + 1)):
            raise ValueError(f"{part_type} report analyses must match the submitted questions.")


DifficultyValue = Literal["easy", "medium", "hard", "unknown"]


class CamelModel(BaseModel):
    """Wire DTO whose fields intentionally use the public camelCase contract."""


class StartMockTestRequest(CamelModel):

    practiceGoal: str | None = Field(default=None, max_length=300)


class SessionQuestion(CamelModel):
    id: str
    text: str
    topic: str
    source: str
    difficulty: DifficultyValue


class SessionPart1Topic(CamelModel):
    topic: str
    questions: list[SessionQuestion]


class SessionPart1(CamelModel):
    topics: list[SessionPart1Topic]


class SessionCueCard(CamelModel):
    id: str
    topic: str
    prompt: str
    bulletPoints: list[str]
    preparationTimeSeconds: int = 60
    speakingTimeSeconds: int = 120
    source: str
    difficulty: DifficultyValue


class SessionPart2(CamelModel):
    cueCard: SessionCueCard


class SessionPart3(CamelModel):
    questions: list[SessionQuestion]


class MockSessionParts(CamelModel):
    part1: SessionPart1
    part2: SessionPart2
    part3: SessionPart3


class MockSessionMetadata(CamelModel):
    retrievalUsed: bool
    candidateCount: int
    composerUsed: bool
    fallbackUsed: bool
    fallbackReason: str | None = None
    createdAt: datetime


class StartMockTestResponse(CamelModel):
    sessionId: str
    practiceGoal: str | None
    mode: Literal["default", "goal_based"]
    parts: MockSessionParts
    metadata: MockSessionMetadata


class EvaluateMockTestResponse(BaseModel):
    mock_test_id: str
    report: MockTestReport


class MockTestSummary(BaseModel):
    id: str
    mode: str = "full_mock"
    overall_band: float | None
    created_at: datetime


class MockTestDetail(BaseModel):
    id: str
    mode: str = "full_mock"
    questions: list[MockQuestion]
    answers: list[MockAnswer]
    report: MockTestReport
    overall_band: float | None
    created_at: datetime
