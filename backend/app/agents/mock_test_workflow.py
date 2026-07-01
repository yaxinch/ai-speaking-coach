from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.agents.mock_test_agent import MockTestAgent
from app.llm.base import LLMProvider
from app.schemas.mock_test import EvaluateMockTestRequest, EvaluateMockTestResponse, validate_report_for_questions
from app.services.mock_test_service import MockTestService
from app.services.audio_asset_service import AudioAssetService


class MockTestWorkflow:
    def __init__(self, llm: LLMProvider, db: Session) -> None:
        self.agent = MockTestAgent(llm)
        self.service = MockTestService(db)

    async def evaluate_and_save(self, request: EvaluateMockTestRequest) -> EvaluateMockTestResponse:
        answers = [answer.model_copy(update={"answer_text": answer.answer_text.strip()}) for answer in request.answers]
        audio_asset_ids = [answer.audio_asset_id for answer in answers if answer.audio_asset_id]
        audio_service = AudioAssetService(self.service.db)
        for asset_id in audio_asset_ids:
            asset = audio_service.get(asset_id)
            if asset is None or asset.status != "pending":
                raise HTTPException(status_code=409, detail="One or more mock test audio recordings are unavailable.")
        report = await self.agent.evaluate(answers)
        try:
            validate_report_for_questions(report, [answer.question for answer in answers])
        except ValueError as exc:
            raise HTTPException(status_code=502, detail="AI returned an incomplete mock test report.") from exc
        record = self.service.create_record(answers, report)
        if audio_asset_ids:
            audio_service.attach(audio_asset_ids, owner_type="mock_test", owner_id=record.id)
        return EvaluateMockTestResponse(mock_test_id=record.id, report=report)
