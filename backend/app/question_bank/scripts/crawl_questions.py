import argparse
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.question_bank.crawler.fetcher import CompliantFetcher, FetchSkipped
from app.question_bank.crawler.parsers import create_parser
from app.question_bank.crawler.source_loader import load_sources


logger = logging.getLogger(__name__)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "source"


def default_sources_path() -> Path:
    local = Path("data/question_bank/sources/question_sources.local.json")
    return local if local.exists() else Path("data/question_bank/sources/question_sources.json")


def _parse_bool(value: str) -> bool:
    lowered = value.lower()
    if lowered in {"true", "1", "yes"}:
        return True
    if lowered in {"false", "0", "no"}:
        return False
    raise argparse.ArgumentTypeError("expected true or false")


def crawl(
    sources_path: Path,
    output_dir: Path,
    cache_dir: Path,
    limit: int,
    dry_run: bool,
    *,
    source_name: str | None = None,
    ignore_cache: bool = False,
    timeout_seconds: float = 15,
    max_retries: int = 2,
    min_delay_seconds: float = 2,
    max_delay_seconds: float = 5,
) -> dict:
    if limit < 1:
        raise ValueError("limit must be at least 1")
    sources = load_sources(sources_path)
    enabled = [source for source in sources if source["enabled"]]
    selected = [source for source in enabled if source_name is None or source["name"] == source_name]
    if source_name and not selected:
        raise ValueError(f"No enabled source matches --source-name: {source_name}")
    planned = [(source, url) for source in selected for url in source["urls"]][:limit]
    summary = {
        "enabled_sources": [source["name"] for source in enabled],
        "planned_urls": [url for _, url in planned],
        "fetched_urls": [],
        "skipped_urls": [],
        "skipped_reasons": {},
        "cache_hits": 0,
        "raw_output_files": [],
        "parsed_question_count": 0,
        "pending_review_count": 0,
        "per_source_question_count": {},
    }
    if dry_run:
        for source, url in planned:
            print(f"DRY RUN [{source['name']}]: {url} (robots not checked; no network request made)")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return summary

    grouped: dict[str, tuple[dict, list[dict]]] = {}
    with CompliantFetcher(
        cache_dir,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        min_delay_seconds=min_delay_seconds,
        max_delay_seconds=max_delay_seconds,
    ) as fetcher:
        for source, url in planned:
            try:
                result = fetcher.fetch(url, ignore_cache=ignore_cache)
                if result is None:
                    continue
                summary["fetched_urls"].append(url)
                if result.from_cache:
                    summary["cache_hits"] += 1
                parser_config = {**source, "source_url": url}
                records = create_parser(source["parser"]).parse(result.html, parser_config)
                if not records:
                    logger.warning("No stable questions parsed from %s; use manual CSV/JSON import", url)
                grouped.setdefault(source["name"], (source, []))[1].extend(records)
            except FetchSkipped as exc:
                logger.warning("Skipped: %s", exc)
                summary["skipped_urls"].append(url)
                summary["skipped_reasons"][url] = str(exc)
            except (httpx.HTTPError, ValueError) as exc:
                reason = f"{type(exc).__name__}: {exc}"
                logger.warning("Skipped %s: %s", url, reason)
                summary["skipped_urls"].append(url)
                summary["skipped_reasons"][url] = reason
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for source, records in grouped.values():
        path = output_dir / f"{_slug(source['name'])}_{timestamp}_raw.json"
        path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {len(records)} raw questions to {path}")
        summary["raw_output_files"].append(str(path))
    summary["parsed_question_count"] = sum(len(records) for _, records in grouped.values())
    summary["pending_review_count"] = sum(
        record.get("status", "pending_review") == "pending_review"
        for _, records in grouped.values()
        for record in records
    )
    summary["per_source_question_count"] = {
        source_name: len(records) for source_name, (_, records) in grouped.items()
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect public practice questions into raw JSON only.")
    parser.add_argument("--sources", type=Path)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--source-name")
    parser.add_argument("--ignore-cache", type=_parse_bool, default=False)
    parser.add_argument("--output-dir", type=Path, default=Path("data/question_bank/raw"))
    parser.add_argument("--cache-dir", type=Path, default=Path("data/question_bank/html_cache"))
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--min-delay", type=float, default=2)
    parser.add_argument("--max-delay", type=float, default=5)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    crawl(
        args.sources or default_sources_path(),
        args.output_dir,
        args.cache_dir,
        args.limit,
        args.dry_run,
        source_name=args.source_name,
        ignore_cache=args.ignore_cache,
        timeout_seconds=args.timeout,
        max_retries=args.max_retries,
        min_delay_seconds=args.min_delay,
        max_delay_seconds=args.max_delay,
    )


if __name__ == "__main__":
    main()
