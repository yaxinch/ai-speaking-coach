def build_examiner_prompt(part_type: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are an IELTS Speaking Examiner. Generate realistic IELTS Speaking "
                "practice questions and return strict JSON only."
            ),
        },
        {
            "role": "user",
            "content": f"""
Input:
- part_type: {part_type}

Rules:
- part1: Generate one short daily-life question.
- part2: Generate one cue card with a topic, 4 bullet points, and a preparation instruction.
- part3: Generate one abstract discussion question related to society, opinions, causes, effects, or comparison.
- The question must sound natural and realistic for IELTS Speaking.
- Do not include explanations.
- Return strict JSON only. Do not wrap it in markdown.

Output JSON schema:
{{
  "part_type": "part1 | part2 | part3",
  "question": "string",
  "cue_card": {{
    "topic": "string",
    "bullet_points": ["string", "string", "string", "string"],
    "preparation_instruction": "string"
  }}
}}

For part1 and part3, set cue_card to null.
""".strip(),
        },
    ]
