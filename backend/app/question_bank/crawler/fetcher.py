import hashlib
import logging
import random
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx


logger = logging.getLogger(__name__)
DEFAULT_USER_AGENT = "AI-Speaking-Coach-QuestionBank/1.0 (low-volume educational review crawler)"
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
BLOCK_PAGE_MARKERS = ("cf-chl-", "cloudflare", "captcha", "verify you are human", "access denied")


class FetchSkipped(RuntimeError):
    pass


class ManualImportRequired(FetchSkipped):
    pass


@dataclass(frozen=True)
class FetchResult:
    url: str
    html: str
    from_cache: bool


class CompliantFetcher:
    def __init__(
        self,
        cache_dir: str | Path,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout_seconds: float = 15,
        max_retries: int = 2,
        min_delay_seconds: float = 2,
        max_delay_seconds: float = 5,
        client: httpx.Client | None = None,
        sleep_fn=time.sleep,
        uniform_fn=random.uniform,
    ):
        if min_delay_seconds < 1 or max_delay_seconds < min_delay_seconds:
            raise ValueError("Request delay must be at least one second and max >= min")
        if not 0 <= max_retries <= 3:
            raise ValueError("max_retries must be between 0 and 3")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.user_agent = user_agent
        self.max_retries = max_retries
        self.min_delay_seconds = min_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.sleep_fn = sleep_fn
        self.uniform_fn = uniform_fn
        self.client = client or httpx.Client(timeout=timeout_seconds, headers={"User-Agent": user_agent}, follow_redirects=True)
        self._owns_client = client is None
        self._robots: dict[str, RobotFileParser] = {}
        self._robots_errors: dict[str, str] = {}
        self._has_requested = False

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def fetch(self, url: str, *, dry_run: bool = False, ignore_cache: bool = False) -> FetchResult | None:
        if dry_run:
            logger.info("DRY RUN: %s (robots not checked; no network request made)", url)
            return None
        if not self._is_allowed(url):
            origin = f"{urlsplit(url).scheme}://{urlsplit(url).netloc}"
            reason = self._robots_errors.get(origin)
            if reason:
                raise FetchSkipped(f"robots.txt validation failed ({reason}): {url}")
            raise FetchSkipped(f"robots.txt disallows: {url}")
        cache_path = self.cache_dir / f"{hashlib.sha256(url.encode('utf-8')).hexdigest()}.html"
        if cache_path.exists() and not ignore_cache:
            return FetchResult(url, cache_path.read_text(encoding="utf-8"), True)
        response = self._request_with_retry(url)
        lowered = response.text[:20000].lower()
        if response.status_code in {401, 403} or any(marker in lowered for marker in BLOCK_PAGE_MARKERS):
            raise ManualImportRequired(f"Access challenge detected; use manual CSV/JSON import: {url}")
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").lower()
        if content_type and "text/html" not in content_type and "application/xhtml+xml" not in content_type:
            raise ManualImportRequired(f"Non-HTML content requires manual review/import: {url}")
        cache_path.write_text(response.text, encoding="utf-8")
        return FetchResult(url, response.text, False)

    def _is_allowed(self, url: str) -> bool:
        parsed = urlsplit(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin in self._robots_errors:
            return False
        if origin not in self._robots:
            robots_url = f"{origin}/robots.txt"
            try:
                response = self._request_with_retry(robots_url)
                if response.status_code != 200:
                    logger.warning("Cannot validate robots.txt (%s): %s", response.status_code, robots_url)
                    self._robots_errors[origin] = f"HTTP {response.status_code}"
                    return False
                parser = RobotFileParser(robots_url)
                parser.parse(response.text.splitlines())
                self._robots[origin] = parser
            except httpx.HTTPError as exc:
                logger.warning("Cannot validate robots.txt for %s: %s", origin, type(exc).__name__)
                self._robots_errors[origin] = type(exc).__name__
                return False
        return self._robots[origin].can_fetch(self.user_agent, url)

    def _request_with_retry(self, url: str) -> httpx.Response:
        last_response: httpx.Response | None = None
        for attempt in range(self.max_retries + 1):
            if self._has_requested:
                self.sleep_fn(self.uniform_fn(self.min_delay_seconds, self.max_delay_seconds))
            self._has_requested = True
            try:
                response = self.client.get(url, headers={"User-Agent": self.user_agent})
            except httpx.TransportError:
                if attempt == self.max_retries:
                    raise
                self.sleep_fn(min(2**attempt, 4))
                continue
            last_response = response
            if response.status_code not in RETRYABLE_STATUSES or attempt == self.max_retries:
                return response
            self.sleep_fn(min(2**attempt, 4))
        assert last_response is not None
        return last_response
