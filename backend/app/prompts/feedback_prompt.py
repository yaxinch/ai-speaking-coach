import json

from app.schemas.agent import ExaminerQuestion


def build_feedback_prompt(part_type: str, question: ExaminerQuestion, user_answer: str) -> list[dict[str, str]]:
    question_payload = question.model_dump()
    return [
        {
            "role": "system",
            "content": (
                "You are an IELTS Speaking Coach. Evaluate answers with practical, "
                "specific IELTS-style feedback. Return strict JSON only."
            ),
        },
        {
            "role": "user",
            "content": f"""
Input:
- part_type: {part_type}
- question: {json.dumps(question_payload, ensure_ascii=False)}
- user_answer: {user_answer}

Scoring criteria:
- Fluency and Coherence
- Lexical Resource
- Grammatical Range and Accuracy
- Pronunciation is not evaluated because this product currently uses text input only.

Rules:
- Give practical, specific, and actionable feedback.
- Do not be overly generous.
- If the answer is too short, mention that clearly.
- The improved answer should preserve the user's original meaning but make it more natural and IELTS-appropriate.
- Return strict JSON only. Do not wrap it in markdown.

Output JSON schema:
{{
  "overall_band_score": 0.0,
  "fluency_score": 0.0,
  "vocabulary_score": 0.0,
  "grammar_score": 0.0,
  "pronunciation_note": "Not evaluated because this MVP uses text input only.",
  "strengths": ["string"],
  "weaknesses": ["string"],
  "improved_answer": "string",
  "action_suggestions": ["string"]
}}
""".strip(),
        },
    ]
