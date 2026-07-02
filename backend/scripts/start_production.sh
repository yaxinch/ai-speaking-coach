#!/bin/sh
set -eu

SEED_FILE="${QUESTION_SEED_FILE:-data/question_bank/seed/seed_questions.json}"
EMBEDDING_BATCH_SIZE="${EMBEDDING_BATCH_SIZE:-50}"

python -m alembic upgrade head
python -m app.question_bank.scripts.import_questions --file "$SEED_FILE"
python -m app.question_bank.scripts.generate_embeddings --batch-size "$EMBEDDING_BATCH_SIZE"

exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
