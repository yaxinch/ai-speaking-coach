from app.agents.feedback_agent import FeedbackAgent
from app.llm.base import LLMProvider
from app.schemas.agent import ExaminerQuestion, PartType
from app.schemas.speaking import VoiceFeedback, VoiceScore


class SpeakingScoringService:
    def __init__(self, llm: LLMProvider) -> None:
        self.agent = FeedbackAgent(llm)

    async def score(
        self,
        *,
        part_type: PartType,
        question: ExaminerQuestion,
        answer_text: str,
        mode: str,
        answer_source: str,
        strict: bool,
    ) -> tuple[VoiceScore, VoiceFeedback]:
        result = await self.agent.evaluate(
            part_type,
            question,
            answer_text,
            answer_source=answer_source,
            mode=mode,
            strict=strict,
        )
        return (
            VoiceScore(
                overall=result.overall_band_score,
                fluency_coherence=result.fluency_score,
                lexical_resource=result.vocabulary_score,
                grammatical_range_accuracy=result.grammar_score,
                pronunciation=None,
                pronunciation_assessment=None,
            ),
            VoiceFeedback(
                summary=result.summary,
                strengths=result.strengths,
                weaknesses=result.weaknesses,
                corrections=result.corrections,
                improved_answer=result.improved_answer,
                next_practice_suggestion=result.next_practice_suggestion
                or (result.action_suggestions[0] if result.action_suggestions else ""),
                pronunciation_note=result.pronunciation_note,
            ),
        )
