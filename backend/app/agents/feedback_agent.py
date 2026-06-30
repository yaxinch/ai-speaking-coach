from app.llm.base import LLMProvider
from app.llm.json_parser import fallback_feedback, parse_json_object
from app.prompts.feedback_prompt import build_feedback_prompt
from app.schemas.agent import ExaminerQuestion, FeedbackResult, PartType


class FeedbackAgent:
    def __init__(self, llm: LLMProvider) -> None:
        self.llm = llm

    async def evaluate(
        self,
        part_type: PartType,
        question: ExaminerQuestion,
        user_answer: str,
        *,
        answer_source: str = "text",
        mode: str = "single-practice",
        strict: bool = False,
    ) -> FeedbackResult:
        raw = await self.llm.chat(
            build_feedback_prompt(part_type, question, user_answer, answer_source=answer_source, mode=mode),
            temperature=0.2,
        )
        try:
            data = parse_json_object(raw)
            feedback = FeedbackResult.model_validate(data)
        except Exception:
            if strict:
                raise ValueError("AI returned an invalid speaking assessment.")
            feedback = fallback_feedback()
        return feedback
