import json
from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.question_bank.models import SpeakingQuestion
from app.question_bank.schemas import QuestionInput
from app.question_bank.crawler.deduper import generate_content_hash


class QuestionRepository:
    def __init__(self, db: Session):
        self.db = db

    def bulk_insert(self, questions: Iterable[QuestionInput | dict]) -> tuple[list[SpeakingQuestion], int]:
        """Insert unseen hashes and return (created rows, duplicate count)."""
        prepared: list[dict] = []
        input_hashes: set[str] = set()
        duplicates = 0
        for item in questions:
            data = item.model_dump() if isinstance(item, QuestionInput) else QuestionInput.model_validate(item).model_dump()
            content_hash = data["content_hash"] or generate_content_hash(data["question"])
            data["content_hash"] = content_hash
            if content_hash in input_hashes:
                duplicates += 1
                continue
            input_hashes.add(content_hash)
            bullets = data.pop("cue_card_bullets")
            data["cue_card_bullets"] = json.dumps(bullets, ensure_ascii=False) if bullets else None
            prepared.append(data)

        existing_hashes: set[str] = set()
        hashes = list(input_hashes)
        for start in range(0, len(hashes), 500):
            existing_hashes.update(
                self.db.scalars(
                    select(SpeakingQuestion.content_hash).where(
                        SpeakingQuestion.content_hash.in_(hashes[start : start + 500])
                    )
                )
            )
        duplicates += len(existing_hashes)
        created = [SpeakingQuestion(**data) for data in prepared if data["content_hash"] not in existing_hashes]
        self.db.add_all(created)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise
        return created, duplicates

    def get_by_hash(self, content_hash: str) -> SpeakingQuestion | None:
        return self.db.scalar(select(SpeakingQuestion).where(SpeakingQuestion.content_hash == content_hash))

    def pending_review(self, limit: int | None = None) -> list[SpeakingQuestion]:
        return self.query(status="pending_review", limit=limit)

    def update_status(self, question_id: str, status: str) -> SpeakingQuestion | None:
        if status not in {"pending_review", "approved", "rejected"}:
            raise ValueError(f"Unsupported review status: {status}")
        row = self.db.get(SpeakingQuestion, question_id)
        if row is None:
            return None
        row.status = status
        self.db.commit()
        self.db.refresh(row)
        return row

    def query(
        self,
        *,
        status: str | None = None,
        part: str | None = None,
        topic: str | None = None,
        difficulty: str | None = None,
        confidence: str | None = None,
        limit: int | None = None,
    ) -> list[SpeakingQuestion]:
        statement = select(SpeakingQuestion).order_by(SpeakingQuestion.created_at, SpeakingQuestion.id)
        for column, value in (
            (SpeakingQuestion.status, status),
            (SpeakingQuestion.part, part),
            (SpeakingQuestion.topic, topic),
            (SpeakingQuestion.difficulty, difficulty),
            (SpeakingQuestion.confidence, confidence),
        ):
            if value is not None:
                statement = statement.where(column == value)
        if limit is not None:
            statement = statement.limit(limit)
        return list(self.db.scalars(statement))

    def approved(
        self,
        *,
        part: str | None = None,
        topic: str | None = None,
        difficulty: str | None = None,
        limit: int | None = None,
    ) -> list[SpeakingQuestion]:
        return self.query(status="approved", part=part, topic=topic, difficulty=difficulty, limit=limit)

    def approved_topic_counts(self, part: str) -> dict[str, int]:
        rows = self.db.execute(
            select(SpeakingQuestion.topic, func.count(SpeakingQuestion.id))
            .where(
                SpeakingQuestion.status == "approved",
                SpeakingQuestion.part == part,
                SpeakingQuestion.topic.is_not(None),
                SpeakingQuestion.topic != "",
            )
            .group_by(SpeakingQuestion.topic)
        )
        return {topic: count for topic, count in rows if topic}

    def approved_with_embeddings(self, *, part: str | None = None) -> list[SpeakingQuestion]:
        statement = select(SpeakingQuestion).where(
            SpeakingQuestion.status == "approved",
            SpeakingQuestion.embedding_vector.is_not(None),
            SpeakingQuestion.embedding_dimensions.is_not(None),
            SpeakingQuestion.embedding_model.is_not(None),
        )
        if part is not None:
            statement = statement.where(SpeakingQuestion.part == part)
        return list(self.db.scalars(statement.order_by(SpeakingQuestion.id)))

    def save_embedding(
        self,
        question: SpeakingQuestion,
        *,
        model: str,
        vector_id: str,
        vector: bytes,
        dimensions: int,
        commit: bool = True,
    ) -> None:
        question.embedding_model = model
        question.embedding_vector_id = vector_id
        question.embedding_vector = vector
        question.embedding_dimensions = dimensions
        if commit:
            self.db.commit()
