import json

from app.schemas.mock_test import MockAnswer


def build_mock_test_prompt() -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": "You are an IELTS Speaking Examiner. Return strict JSON only.",
        },
        {
            "role": "user",
            "content": """
Generate one coherent IELTS Speaking mock test.

Rules:
- Return exactly 4 Part 1 questions with question_index 1-4.
- Return exactly 1 Part 2 cue card with question_index 1 and four bullet points.
- Return exactly 3 Part 3 questions with question_index 1-3.
- Part 3 questions should naturally extend the Part 2 topic.
- Part 1 and Part 3 cue_card must be null.
- Do not include explanations or markdown.

Output schema:
{
  "questions": [
    {
      "part_type": "part1 | part2 | part3",
      "question_index": 1,
      "question": "string",
      "cue_card": null | {
        "topic": "string",
        "bullet_points": ["string", "string", "string", "string"],
        "preparation_instruction": "string"
      }
    }
  ]
}
""".strip(),
        },
    ]


def build_mock_session_composer_prompt(
    practice_goal: str,
    part1_candidates: list[dict],
    part2_candidates: list[dict],
    part3_candidates: list[dict],
) -> list[dict[str, str]]:
    payload = {
        "practiceGoal": practice_goal,
        "part1Candidates": part1_candidates,
        "part2Candidates": part2_candidates,
        "part3Candidates": part3_candidates,
    }
    return [
        {
            "role": "system",
            "content": "You compose IELTS Speaking sessions from an approved candidate list. Return strict JSON only.",
        },
        {
            "role": "user",
            "content": f"""
Select a coherent IELTS Speaking session for the user's practice goal.

Candidates:
{json.dumps(payload, ensure_ascii=False)}

Rules:
- Select exactly two Part 1 topics and exactly three Part 1 question IDs under each topic.
- Select exactly one Part 2 cue card ID.
- Select exactly four Part 3 question IDs, preferably related to the selected Part 2 topic.
- Every ID must come from the matching candidate list.
- Do not rewrite, invent, or return question text.
- Do not repeat an ID.
- Return JSON only, without markdown.

Output:
{{
  "part1": {{"topics": [{{"topic": "candidate topic", "questionIds": ["id", "id", "id"]}}]}},
  "part2": {{"cueCardId": "id"}},
  "part3": {{"questionIds": ["id", "id", "id", "id"]}}
}}
""".strip(),
        },
    ]


def build_mock_test_feedback_prompt(answers: list[MockAnswer]) -> list[dict[str, str]]:
    payload = [answer.model_dump() for answer in answers]
    counts = {part: sum(answer.part_type == part for answer in answers) for part in ("part1", "part2", "part3")}
    return [
        {
            "role": "system",
            "content": "You are an IELTS Speaking Coach. Return strict JSON only.",
        },
        {
            "role": "user",
            "content": f"""
Evaluate this complete text-based IELTS Speaking mock test:
{json.dumps(payload, ensure_ascii=False)}

Rules:
- Evaluate fluency/coherence, lexical resource, and grammatical range/accuracy from text.
- Do not evaluate pronunciation.
- Return one overall assessment, feedback for all three parts, and one analysis per question.
- part1_feedback.question_analyses must contain exactly {counts['part1']} items with sequential indexes.
- part2_feedback.question_analyses must contain exactly {counts['part2']} item with sequential indexes.
- part3_feedback.question_analyses must contain exactly {counts['part3']} items with sequential indexes.
- Preserve each question_index exactly.
- Be specific, practical, and not overly generous.
- Return strict JSON only, without markdown.

Output schema:
{{
  "overall_band_score": 0.0,
  "key_strengths": ["string"],
  "key_weaknesses": ["string"],
  "action_plan": ["string"],
  "part1_feedback": {{
    "band_estimate": 0.0,
    "summary": "string",
    "strengths": ["string"],
    "weaknesses": ["string"],
    "question_analyses": [
      {{
        "question_index": 1,
        "band_estimate": 0.0,
        "feedback": "string",
        "strengths": ["string"],
        "weaknesses": ["string"],
        "improved_answer": "string"
      }}
    ]
  }},
  "part2_feedback": {{
    "band_estimate": 0.0,
    "summary": "string",
    "strengths": ["string"],
    "weaknesses": ["string"],
    "question_analyses": [
      {{ "question_index": 1, "band_estimate": 0.0, "feedback": "string", "strengths": ["string"], "weaknesses": ["string"], "improved_answer": "string" }}
    ]
  }},
  "part3_feedback": {{
    "band_estimate": 0.0,
    "summary": "string",
    "strengths": ["string"],
    "weaknesses": ["string"],
            "question_analyses": [{{ "question_index": 1, "band_estimate": 0.0, "feedback": "repeat this object for every submitted Part 3 question", "strengths": ["string"], "weaknesses": ["string"], "improved_answer": "string" }}]
  }}
}}
""".strip(),
        },
    ]
