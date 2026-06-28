from app.llm.base import LLMProvider
from app.llm.json_parser import parse_json_object
from app.prompts.examiner_prompt import build_examiner_prompt
from app.schemas.agent import ExaminerQuestion, PartType


class ExaminerAgent:
    def __init__(self, llm: LLMProvider) -> None:
        self.llm = llm

    async def generate_question(self, part_type: PartType) -> ExaminerQuestion:
        raw = await self.llm.chat(build_examiner_prompt(part_type), temperature=0.8)
        data = parse_json_object(raw)
        data["part_type"] = part_type
        if part_type in {"part1", "part3"}:
            data["cue_card"] = None
        return ExaminerQuestion.model_validate(data)
