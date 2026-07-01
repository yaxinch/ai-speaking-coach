import json
import random

from sqlalchemy.orm import Session

from app.question_bank.crawler.cleaner import clean_question
from app.question_bank.crawler.deduper import dedupe_questions, generate_content_hash
from app.question_bank.crawler.difficulty_classifier import classify_difficulty
from app.question_bank.crawler.topic_classifier import classify_topic
from app.question_bank.models import SpeakingQuestion
from app.question_bank.repository import QuestionRepository


def build_embedding_text(question: dict) -> str:
    lines = [f"Part: {question['part']}"]
    if question.get("topic"):
        lines.append(f"Topic: {question['topic']}")
    if question.get("difficulty"):
        lines.append(f"Difficulty: {question['difficulty']}")
    lines.append(f"Question: {question['question']}")
    bullets = question.get("cue_card_bullets") or []
    if bullets:
        lines.append("Cue card bullets: " + "; ".join(bullets))
    return "\n".join(lines)


def prepare_questions(records: list[dict]) -> list[dict]:
    prepared: list[dict] = []
    for record in records:
        cleaned = clean_question(record)
        if cleaned is None:
            continue
        cleaned["topic"] = cleaned.get("topic") or classify_topic(cleaned)
        cleaned["difficulty"] = cleaned.get("difficulty") or classify_difficulty(cleaned)
        cleaned["content_hash"] = generate_content_hash(cleaned["question"])
        cleaned["status"] = cleaned.get("status") or "pending_review"
        cleaned["embedding_text"] = build_embedding_text(cleaned)
        prepared.append(cleaned)
    return dedupe_questions(prepared)


class QuestionBankService:
    """Read-only access to reviewed practice questions."""

    def __init__(self, db: Session, rng: random.Random | None = None):
        self.repository = QuestionRepository(db)
        self.rng = rng or random.SystemRandom()

    def questions(
        self,
        *,
        part: str | None = None,
        topic: str | None = None,
        difficulty: str | None = None,
    ) -> list[SpeakingQuestion]:
        return self.repository.approved(part=part, topic=topic, difficulty=difficulty)

    def eligible_part1_topics(self, minimum_questions: int = 3) -> list[str]:
        return [topic for topic, count in self.repository.approved_topic_counts("part1").items() if count >= minimum_questions]

    def random_questions(self, rows: list[SpeakingQuestion], count: int) -> list[SpeakingQuestion]:
        if len(rows) < count:
            raise ValueError(f"Question bank contains only {len(rows)} eligible rows; {count} are required.")
        return self.rng.sample(rows, count)

    def random_part2(self) -> SpeakingQuestion:
        rows = [row for row in self.questions(part="part2") if self.cue_card_bullets(row)]
        return self.random_questions(rows, 1)[0]

    @staticmethod
    def cue_card_bullets(row: SpeakingQuestion) -> list[str]:
        if not row.cue_card_bullets:
            return []
        try:
            value = json.loads(row.cue_card_bullets)
        except (TypeError, json.JSONDecodeError):
            return []
        return [str(item).strip() for item in value if str(item).strip()] if isinstance(value, list) else []

    @staticmethod
    def topic(row: SpeakingQuestion) -> str:
        return (row.topic or "General").strip() or "General"

    @staticmethod
    def difficulty(row: SpeakingQuestion) -> str:
        return row.difficulty if row.difficulty in {"easy", "medium", "hard"} else "unknown"
