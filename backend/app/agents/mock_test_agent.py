from fastapi import HTTPException
from pydantic import ValidationError

from app.llm.base import LLMProvider
from app.llm.json_parser import parse_json_object
from app.prompts.mock_test_prompt import build_mock_test_feedback_prompt, build_mock_test_prompt
from app.schemas.mock_test import GenerateMockTestResponse, MockAnswer, MockTestReport


class MockTestAgent:
    def __init__(self, llm: LLMProvider) -> None:
        self.llm = llm

    async def generate(self) -> GenerateMockTestResponse:
        raw = await self.llm.chat(build_mock_test_prompt(), temperature=0.7)
        try:
            return GenerateMockTestResponse.model_validate(parse_json_object(raw))
        except (ValueError, ValidationError) as exc:
            raise HTTPException(status_code=502, detail="AI returned an invalid full mock test.") from exc

    async def evaluate(self, answers: list[MockAnswer]) -> MockTestReport:
        raw = await self.llm.chat(build_mock_test_feedback_prompt(answers), temperature=0.2)
        try:
            return MockTestReport.model_validate(parse_json_object(raw))
        except (ValueError, ValidationError) as exc:
            raise HTTPException(status_code=502, detail="AI returned an incomplete mock test report.") from exc
