import argparse
import csv
import json
from pathlib import Path

from app.database import SessionLocal
from app.question_bank.repository import QuestionRepository
from app.question_bank.service import prepare_questions


def load_import_records(path: Path) -> list[dict]:
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as handle:
            records = [dict(row) for row in csv.DictReader(handle)]
        return [record for record in records if record.get("status", "").strip() == "approved"]
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("Import JSON must contain a list")
    for record in records:
        record.setdefault("status", "pending_review")
    return records


def import_file(path: Path) -> tuple[int, int]:
    prepared = prepare_questions(load_import_records(path))
    with SessionLocal() as db:
        created, duplicates = QuestionRepository(db).bulk_insert(prepared)
    return len(created), duplicates


def main() -> None:
    parser = argparse.ArgumentParser(description="The only pipeline command that writes questions to SQLite.")
    parser.add_argument("--file", required=True, type=Path)
    args = parser.parse_args()
    created, duplicates = import_file(args.file)
    print(f"Imported {created} questions; skipped {duplicates} duplicates")


if __name__ == "__main__":
    main()
