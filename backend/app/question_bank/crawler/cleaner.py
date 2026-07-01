import html
import re
import unicodedata


PART_ALIASES = {
    "1": "part1",
    "part 1": "part1",
    "part1": "part1",
    "2": "part2",
    "part 2": "part2",
    "part2": "part2",
    "3": "part3",
    "part 3": "part3",
    "part3": "part3",
}
REJECT_MARKERS = ("sample answer", "model answer", "band 9 answer", "course", "subscribe", "copyright")


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = html.unescape(unicodedata.normalize("NFKC", value))
    translations = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", "–": "-", "—": "-", "…": "..."})
    value = value.translate(translations)
    value = re.sub(r"\s+", " ", value).strip()
    return value or None


def normalize_part(value: str | None) -> str | None:
    return PART_ALIASES.get((value or "").lower().strip())


def _clean_bullets(value) -> list[str] | None:
    if not value:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("["):
            try:
                import json

                parsed = json.loads(stripped)
                value = parsed if isinstance(parsed, list) else [value]
            except json.JSONDecodeError:
                value = re.split(r"(?:\r?\n|[•▪])", value)
        else:
            value = re.split(r"(?:\r?\n|[•▪])", value)
    bullets = []
    for item in value:
        cleaned = clean_text(str(item).lstrip("-*•▪ "))
        if cleaned and 2 <= len(cleaned) <= 300 and not any(marker in cleaned.lower() for marker in REJECT_MARKERS):
            bullets.append(cleaned)
    return bullets or None


def clean_question(record: dict) -> dict | None:
    part = normalize_part(record.get("part") or record.get("part_type"))
    question = clean_text(record.get("question"))
    if part is None or question is None or not 5 <= len(question) <= 1000:
        return None
    lowered = question.lower()
    if any(marker in lowered for marker in REJECT_MARKERS):
        return None
    if not (question.endswith("?") or (part == "part2" and lowered.startswith("describe "))):
        return None
    cleaned = dict(record)
    cleaned.update(
        part=part,
        question=question,
        cue_card_title=clean_text(record.get("cue_card_title")),
        cue_card_bullets=_clean_bullets(record.get("cue_card_bullets")),
        raw_text=clean_text(record.get("raw_text")),
    )
    for key in (
        "topic",
        "sub_topic",
        "difficulty",
        "source_name",
        "source_url",
        "source_type",
        "source_format",
        "confidence",
        "season",
    ):
        if key in cleaned:
            cleaned[key] = clean_text(cleaned.get(key))
    return cleaned
