import json
import re
from typing import Any

from app.schemas.agent import FeedbackResult


def parse_json_object(raw: str) -> dict[str, Any]:
    candidates = [raw.strip()]

    code_block = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL | re.IGNORECASE)
    if code_block:
        candidates.append(code_block.group(1).strip())

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(raw[start : end + 1])

    for candidate in candidates:
        try:
            value = json.loads(candidate)
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            continue

    raise ValueError("Could not parse a JSON object from the LLM response.")


def fallback_feedback() -> FeedbackResult:
    return FeedbackResult(
        overall_band_score=None,
        fluency_score=None,
        vocabulary_score=None,
        grammar_score=None,
        pronunciation_note="Not evaluated because this MVP uses text input only.",
        strengths=[],
        weaknesses=["The AI feedback response could not be parsed. Please try again."],
        improved_answer="",
        action_suggestions=["Regenerate feedback or submit a clearer answer."],
    )
