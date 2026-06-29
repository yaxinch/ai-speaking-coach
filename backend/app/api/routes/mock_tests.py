from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.mock_test_agent import MockTestAgent
from app.agents.mock_test_workflow import MockTestWorkflow
from app.database import get_db
from app.llm.deepseek_provider import DeepSeekProvider
from app.schemas.mock_test import (
    EvaluateMockTestRequest,
    EvaluateMockTestResponse,
    GenerateMockTestResponse,
    MockTestDetail,
    MockTestSummary,
)
from app.services.mock_test_service import MockTestService

router = APIRouter()


@router.post("/generate", response_model=GenerateMockTestResponse)
async def generate_mock_test() -> GenerateMockTestResponse:
    return await MockTestAgent(DeepSeekProvider()).generate()


@router.post("/evaluate", response_model=EvaluateMockTestResponse)
async def evaluate_mock_test(
    request: EvaluateMockTestRequest,
    db: Session = Depends(get_db),
) -> EvaluateMockTestResponse:
    return await MockTestWorkflow(DeepSeekProvider(), db).evaluate_and_save(request)


@router.get("", response_model=list[MockTestSummary])
def list_mock_tests(db: Session = Depends(get_db)) -> list[MockTestSummary]:
    return MockTestService(db).list_records()


@router.get("/{mock_test_id}", response_model=MockTestDetail)
def get_mock_test(mock_test_id: str, db: Session = Depends(get_db)) -> MockTestDetail:
    record = MockTestService(db).get_record(mock_test_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Mock test record not found.")
    return record
