from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.schemas.agent import CueCard, PartType
from app.schemas.speaking import VoiceFeedback, VoiceScore


EXPECTED_PART_COUNTS: dict[PartType, int] = {"part1": 4, "part2": 1, "part3": 3}


class MockQuestion(BaseModel):
    part_type: PartType
    question_index: int = Field(ge=1)
    question: str
    cue_card: CueCard | None = None


def validate_question_set(questions: list[MockQuestion]) -> list[MockQuestion]:
    if len(questions) != 8:
        raise ValueError("A full mock test must contain exactly 8 questions.")
    for part_type, count in EXPECTED_PART_COUNTS.items():
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

    @model_validator(mode="after")
    def validate_analysis_counts(self):
        parts = {
            "part1": self.part1_feedback,
            "part2": self.part2_feedback,
            "part3": self.part3_feedback,
        }
        for part_type, feedback in parts.items():
            count = EXPECTED_PART_COUNTS[part_type]
            if len(feedback.question_analyses) != count:
                raise ValueError(f"{part_type} must contain exactly {count} question analyses.")
            if sorted(item.question_index for item in feedback.question_analyses) != list(range(1, count + 1)):
                raise ValueError(f"{part_type} analysis indexes must be sequential.")
        return self


class EvaluateMockTestRequest(BaseModel):
    answers: list[MockAnswer]

    @model_validator(mode="after")
    def validate_answers(self):
        if len(self.answers) != 8:
            raise ValueError("A full mock test requires exactly 8 answers.")
        questions = [answer.question for answer in self.answers]
        validate_question_set(questions)
        for answer in self.answers:
            if not answer.answer_text.strip():
                raise ValueError("Every mock test answer must contain text.")
            if answer.part_type != answer.question.part_type or answer.question_index != answer.question.question_index:
                raise ValueError("Answer metadata must match its question.")
        return self


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
