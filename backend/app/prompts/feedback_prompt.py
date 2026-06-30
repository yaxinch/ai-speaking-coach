import json

from app.schemas.agent import ExaminerQuestion


def build_feedback_prompt(
    part_type: str,
    question: ExaminerQuestion,
    user_answer: str,
    *,
    answer_source: str = "text",
    mode: str = "single-practice",
) -> list[dict[str, str]]:
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
- answer_source: {answer_source}
- mode: {mode}

Scoring criteria:
- Fluency and Coherence
- Lexical Resource
- Grammatical Range and Accuracy
- Pronunciation cannot be evaluated accurately from text or an ASR transcript; return null and explain this limitation.

Rules:
- Give practical, specific, and actionable feedback.
- Do not be overly generous.
- If the answer is too short, mention that clearly.
- The improved answer should preserve the user's original meaning but make it more natural and IELTS-appropriate.
- If answer_source is transcript, allow for possible ASR errors and do not treat obvious transcription artifacts as pronunciation evidence.
- Return strict JSON only. Do not wrap it in markdown.

Output JSON schema:
{{
  "overall_band_score": 0.0,
  "fluency_score": 0.0,
  "vocabulary_score": 0.0,
  "grammar_score": 0.0,
  "pronunciation_score": null,
  "pronunciation_note": "Pronunciation cannot be evaluated accurately from a transcript alone.",
  "summary": "string",
  "strengths": ["string"],
  "weaknesses": ["string"],
  "corrections": [{{"original": "string", "corrected": "string", "reason": "string"}}],
  "improved_answer": "string",
  "action_suggestions": ["string"],
  "next_practice_suggestion": "string"
}}
""".strip(),
        },
    ]
