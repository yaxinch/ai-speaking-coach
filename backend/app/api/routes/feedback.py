from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.workflow import PracticeWorkflow
from app.database import get_db
from app.llm.base import LLMProvider
from app.providers.factory import get_llm_provider
from app.schemas.agent import EvaluateAnswerRequest, EvaluateAnswerResponse

router = APIRouter()


@router.post("/evaluate", response_model=EvaluateAnswerResponse)
async def evaluate_answer(
    request: EvaluateAnswerRequest,
    db: Session = Depends(get_db),
    llm: LLMProvider = Depends(get_llm_provider),
) -> EvaluateAnswerResponse:
    if not request.user_answer.strip():
        raise HTTPException(status_code=400, detail="Answer cannot be empty.")
    workflow = PracticeWorkflow(llm, db)
    return await workflow.evaluate_and_save(request)
