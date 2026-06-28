from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.workflow import PracticeWorkflow
from app.database import get_db
from app.llm.deepseek_provider import DeepSeekProvider
from app.schemas.agent import EvaluateAnswerRequest, EvaluateAnswerResponse

router = APIRouter()


@router.post("/evaluate", response_model=EvaluateAnswerResponse)
async def evaluate_answer(
    request: EvaluateAnswerRequest,
    db: Session = Depends(get_db),
) -> EvaluateAnswerResponse:
    if not request.user_answer.strip():
        raise HTTPException(status_code=400, detail="Answer cannot be empty.")
    workflow = PracticeWorkflow(DeepSeekProvider(), db)
    return await workflow.evaluate_and_save(request)
