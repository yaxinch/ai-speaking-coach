from sqlalchemy.orm import Session

from app.agents.feedback_agent import FeedbackAgent
from app.llm.base import LLMProvider
from app.schemas.agent import EvaluateAnswerRequest, EvaluateAnswerResponse
from app.services.practice_service import PracticeService


class PracticeWorkflow:
    def __init__(self, llm: LLMProvider, db: Session) -> None:
        self.feedback_agent = FeedbackAgent(llm)
        self.practice_service = PracticeService(db)

    async def evaluate_and_save(self, request: EvaluateAnswerRequest) -> EvaluateAnswerResponse:
        feedback = await self.feedback_agent.evaluate(
            request.part_type,
            request.question,
            request.user_answer.strip(),
        )
        record = self.practice_service.create_record(
            part_type=request.part_type,
            question=request.question,
            user_answer=request.user_answer.strip(),
            feedback=feedback,
        )
        return EvaluateAnswerResponse(practice_id=record.id, feedback=feedback)
