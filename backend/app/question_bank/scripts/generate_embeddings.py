import argparse

from app.config import get_settings
from app.database import SessionLocal
from app.question_bank.embedding_service import EmbeddingService, EmbeddingUnavailable, encode_vector, vector_fingerprint
from app.question_bank.repository import QuestionRepository


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate persistent embeddings for approved speaking questions.")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--part", choices=("part1", "part2", "part3"))
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def generate_embeddings(
    *,
    batch_size: int = 50,
    limit: int | None = None,
    part: str | None = None,
    force: bool = False,
    embedding: EmbeddingService | None = None,
    session_factory=SessionLocal,
) -> tuple[int, int]:
    if batch_size < 1:
        raise SystemExit("--batch-size must be positive")
    embedding = embedding or EmbeddingService(get_settings())
    with session_factory() as db:
        repository = QuestionRepository(db)
        rows = repository.approved(part=part)
        pending = []
        for row in rows:
            text = row.embedding_text or row.question
            fingerprint = vector_fingerprint(embedding.model, text)
            if force or row.embedding_vector is None or row.embedding_vector_id != fingerprint:
                pending.append((row, text, fingerprint))
        if limit is not None:
            pending = pending[:limit]
        processed = 0
        for start in range(0, len(pending), batch_size):
            batch = pending[start : start + batch_size]
            try:
                vectors = embedding.embed_documents([text for _, text, _ in batch])
            except EmbeddingUnavailable as exc:
                raise SystemExit(str(exc)) from exc
            for (row, _, fingerprint), vector in zip(batch, vectors):
                repository.save_embedding(
                    row,
                    model=embedding.model,
                    vector_id=fingerprint,
                    vector=encode_vector(vector),
                    dimensions=embedding.dimensions,
                    commit=False,
                )
            db.commit()
            processed += len(batch)
            print(f"Embedded {processed}/{len(pending)} approved questions.")
        skipped = len(rows) - len(pending)
        print(f"Embedding generation complete: updated={processed}, skipped={skipped}")
        return processed, skipped


def main() -> None:
    args = parse_args()
    generate_embeddings(
        batch_size=args.batch_size,
        limit=args.limit,
        part=args.part,
        force=args.force,
    )


if __name__ == "__main__":
    main()
