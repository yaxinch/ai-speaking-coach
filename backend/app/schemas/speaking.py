from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.agent import Correction, ExaminerQuestion, PartType, PronunciationAssessment


SpeakingMode = Literal["single-practice", "mock-test"]


class TTSRequest(BaseModel):
    question_id: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=1000)
    voice: str = "Kore"
    accent: Literal["british", "american"] = "british"
    speed: float = Field(default=0.95, ge=0.75, le=1.25)


class VoiceScore(BaseModel):
    overall: float | None = None
    fluency_coherence: float | None = None
    lexical_resource: float | None = None
    grammatical_range_accuracy: float | None = None
    pronunciation: float | None = None
    pronunciation_assessment: PronunciationAssessment | None = None


class VoiceFeedback(BaseModel):
    summary: str = ""
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    corrections: list[Correction] = Field(default_factory=list)
    improved_answer: str = ""
    next_practice_suggestion: str = ""
    pronunciation_note: str = "Pronunciation cannot be evaluated accurately from a transcript alone."


class VoiceAnswerResponse(BaseModel):
    practice_id: str | None = None
    audio_asset_id: str
    audio_url: str
    transcript: str
    asr_provider: str
    is_mock_transcript: bool = False
    score: VoiceScore
    feedback: VoiceFeedback


class VoiceQuestionPayload(BaseModel):
    part_type: PartType
    question: str
    cue_card: dict | None = None

    def to_examiner_question(self) -> ExaminerQuestion:
        return ExaminerQuestion.model_validate(self.model_dump())
