from fastapi import APIRouter, Depends

from app.agents.examiner_agent import ExaminerAgent
from app.llm.base import LLMProvider
from app.providers.factory import get_llm_provider
from app.schemas.agent import ExaminerQuestion, GenerateQuestionRequest

router = APIRouter()


@router.post("/generate", response_model=ExaminerQuestion)
async def generate_question(
    request: GenerateQuestionRequest,
    llm: LLMProvider = Depends(get_llm_provider),
) -> ExaminerQuestion:
    agent = ExaminerAgent(llm)
    return await agent.generate_question(request.part_type)
