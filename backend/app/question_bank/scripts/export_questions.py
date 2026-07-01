import argparse
import csv
import json
from pathlib import Path


CSV_FIELDS = [
    "part",
    "question",
    "cue_card_title",
    "cue_card_bullets",
    "topic",
    "sub_topic",
    "difficulty",
    "source_name",
    "source_url",
    "source_type",
    "source_format",
    "confidence",
    "season",
    "raw_text",
    "content_hash",
    "status",
    "embedding_text",
    "embedding_model",
    "embedding_vector_id",
]


def latest_cleaned(directory: Path) -> Path:
    candidates = sorted(directory.glob("speaking_questions_cleaned_*.json"), key=lambda path: path.stat().st_mtime)
    if not candidates:
        raise FileNotFoundError(f"No cleaned JSON files found in {directory}")
    return candidates[-1]


def export_review(input_path: Path, output_path: Path, status: str) -> int:
    records = json.loads(input_path.read_text(encoding="utf-8"))
    selected = [record for record in records if record.get("status", "pending_review") == status]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for record in selected:
            row = {field: record.get(field) for field in CSV_FIELDS}
            row["cue_card_bullets"] = json.dumps(record.get("cue_card_bullets"), ensure_ascii=False) if record.get(
                "cue_card_bullets"
            ) else ""
            writer.writerow(row)
    return len(selected)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export cleaned questions for human review.")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--cleaned-dir", type=Path, default=Path("data/question_bank/cleaned"))
    parser.add_argument("--status", default="pending_review", choices=["pending_review", "approved", "rejected"])
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    input_path = args.input or latest_cleaned(args.cleaned_dir)
    count = export_review(input_path, args.output, args.status)
    print(f"Exported {count} questions to {args.output}")


if __name__ == "__main__":
    main()
