import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from app.question_bank.service import prepare_questions


def _input_files(path: Path) -> list[Path]:
    return sorted(path.glob("*_raw.json")) if path.is_dir() else [path]


def clean(input_path: Path | list[Path], output_dir: Path) -> Path:
    records: list[dict] = []
    inputs = input_path if isinstance(input_path, list) else [input_path]
    for configured_path in inputs:
        for path in _input_files(configured_path):
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                raise ValueError(f"Expected a JSON list in {path}")
            records.extend(data)
    prepared = prepare_questions(records)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = output_dir / f"speaking_questions_cleaned_{timestamp}.json"
    output.write_text(json.dumps(prepared, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean, classify, and deduplicate raw question JSON.")
    parser.add_argument("--input", required=True, type=Path, action="append", help="Repeat to merge selected raw inputs")
    parser.add_argument("--output-dir", type=Path, default=Path("data/question_bank/cleaned"))
    args = parser.parse_args()
    output = clean(args.input, args.output_dir)
    print(f"Wrote cleaned questions to {output}")


if __name__ == "__main__":
    main()
