import json
from pathlib import Path
from urllib.parse import urlparse


SOURCE_TYPES = {"official_sample", "education_site", "recent_recalled", "predicted", "llm_generated"}
CONFIDENCE_LEVELS = {"high", "medium_high", "medium", "low"}


def load_sources(path: str | Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Sources configuration must contain a JSON list")
    validated = []
    for index, source in enumerate(data):
        required = {"name", "base_url", "urls", "parser", "source_type", "confidence", "enabled"}
        missing = required - source.keys()
        if missing:
            raise ValueError(f"Source {index} is missing: {', '.join(sorted(missing))}")
        if source["source_type"] not in SOURCE_TYPES or source["confidence"] not in CONFIDENCE_LEVELS:
            raise ValueError(f"Source {source['name']} has unsupported classification")
        base = urlparse(source["base_url"])
        if base.scheme not in {"http", "https"} or not base.netloc:
            raise ValueError(f"Source {source['name']} has an invalid base_url")
        for url in source["urls"]:
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or parsed.netloc != base.netloc:
                raise ValueError(f"URL must use the configured origin for {source['name']}: {url}")
        validated.append(source)
    return validated
