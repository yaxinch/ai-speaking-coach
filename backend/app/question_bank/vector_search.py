from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.question_bank.embedding_service import decode_vector
from app.question_bank.models import SpeakingQuestion
from app.question_bank.repository import QuestionRepository


@dataclass(frozen=True)
class ScoredQuestion:
    question: SpeakingQuestion
    score: float


class VectorSearchService:
    def __init__(self, db: Session, *, model: str, dimensions: int):
        self.repository = QuestionRepository(db)
        self.model = model
        self.dimensions = dimensions

    def search(self, query_vector: list[float], *, part: str, top_k: int) -> list[ScoredQuestion]:
        if len(query_vector) != self.dimensions:
            raise ValueError("Query embedding dimensions do not match the configured index.")
        scored: list[ScoredQuestion] = []
        for row in self.repository.approved_with_embeddings(part=part):
            if row.embedding_model != self.model or row.embedding_dimensions != self.dimensions or not row.embedding_vector:
                continue
            try:
                stored = decode_vector(row.embedding_vector, row.embedding_dimensions)
            except ValueError:
                continue
            scored.append(ScoredQuestion(row, sum(left * right for left, right in zip(query_vector, stored))))
        scored.sort(key=lambda item: (-item.score, item.question.id))
        return scored[:top_k]
