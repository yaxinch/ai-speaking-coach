from fastapi import APIRouter

from app.agents.examiner_agent import ExaminerAgent
from app.llm.deepseek_provider import DeepSeekProvider
from app.schemas.agent import ExaminerQuestion, GenerateQuestionRequest

router = APIRouter()


@router.post("/generate", response_model=ExaminerQuestion)
async def generate_question(request: GenerateQuestionRequest) -> ExaminerQuestion:
    agent = ExaminerAgent(DeepSeekProvider())
    return await agent.generate_question(request.part_type)
