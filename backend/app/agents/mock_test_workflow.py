from sqlalchemy.orm import Session

from app.agents.mock_test_agent import MockTestAgent
from app.llm.base import LLMProvider
from app.schemas.mock_test import EvaluateMockTestRequest, EvaluateMockTestResponse
from app.services.mock_test_service import MockTestService


class MockTestWorkflow:
    def __init__(self, llm: LLMProvider, db: Session) -> None:
        self.agent = MockTestAgent(llm)
        self.service = MockTestService(db)

    async def evaluate_and_save(self, request: EvaluateMockTestRequest) -> EvaluateMockTestResponse:
        answers = [answer.model_copy(update={"answer_text": answer.answer_text.strip()}) for answer in request.answers]
        report = await self.agent.evaluate(answers)
        record = self.service.create_record(answers, report)
        return EvaluateMockTestResponse(mock_test_id=record.id, report=report)
