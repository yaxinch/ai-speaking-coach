import json


def build_section_practice_selector_prompt(
    part: str,
    practice_goal: str,
    candidates: list[dict],
) -> list[dict[str, str]]:
    payload = {"part": part, "practiceGoal": practice_goal, "candidates": candidates}
    return [
        {
            "role": "system",
            "content": "You are an IELTS Speaking practice question selector. Return strict JSON only.",
        },
        {
            "role": "user",
            "content": f"""
Select exactly one question that best matches the user's practice goal.

Input:
{json.dumps(payload, ensure_ascii=False)}

Rules:
- Select only from the provided candidate IDs.
- The selected item must belong to {part}.
- Do not rewrite question text.
- Do not create a new question.
- Do not return explanations or markdown.
- Return valid JSON only.

Output:
{{"selectedId": "candidate-id"}}
""".strip(),
        },
    ]
