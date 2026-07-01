import hashlib
import re
import unicodedata


CONFIDENCE_RANK = {"high": 4, "medium_high": 3, "medium": 2, "low": 1}


def normalize_question_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).lower()
    normalized = "".join(character if character.isalnum() else " " for character in normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def generate_content_hash(text: str) -> str:
    return hashlib.sha256(normalize_question_text(text).encode("utf-8")).hexdigest()


def dedupe_questions(questions: list[dict]) -> list[dict]:
    """Keep the highest-confidence item; preserve input order for ties."""
    winners: dict[str, tuple[int, dict]] = {}
    for index, question in enumerate(questions):
        content_hash = question.get("content_hash") or generate_content_hash(question.get("question", ""))
        candidate = {**question, "content_hash": content_hash}
        existing = winners.get(content_hash)
        if existing is None or CONFIDENCE_RANK.get(candidate.get("confidence", "low"), 0) > CONFIDENCE_RANK.get(
            existing[1].get("confidence", "low"), 0
        ):
            winners[content_hash] = (existing[0] if existing else index, candidate)
    return [item for _, item in sorted(winners.values(), key=lambda pair: pair[0])]
