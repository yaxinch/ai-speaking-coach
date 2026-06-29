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


def build_mock_test_feedback_prompt(answers: list[MockAnswer]) -> list[dict[str, str]]:
    payload = [answer.model_dump() for answer in answers]
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
- part1_feedback.question_analyses must contain exactly 4 items with indexes 1-4.
- part2_feedback.question_analyses must contain exactly 1 item with index 1.
- part3_feedback.question_analyses must contain exactly 3 items with indexes 1-3.
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
    "question_analyses": [
      {{ "question_index": 1, "band_estimate": 0.0, "feedback": "string", "strengths": ["string"], "weaknesses": ["string"], "improved_answer": "string" }},
      {{ "question_index": 2, "band_estimate": 0.0, "feedback": "string", "strengths": ["string"], "weaknesses": ["string"], "improved_answer": "string" }},
      {{ "question_index": 3, "band_estimate": 0.0, "feedback": "string", "strengths": ["string"], "weaknesses": ["string"], "improved_answer": "string" }}
    ]
  }}
}}
""".strip(),
        },
    ]
