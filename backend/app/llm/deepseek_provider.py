import asyncio
import logging
import random

import httpx
from fastapi import HTTPException

from app.config import Settings, get_settings


logger = logging.getLogger(__name__)


class DeepSeekProvider:
    MAX_RETRIES = 3
    RETRY_BASE_SECONDS = 2.0
    RETRYABLE_STATUSES = {429, 500, 502, 503, 504}

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep=asyncio.sleep,
        jitter=random.random,
    ) -> None:
        self.settings = settings or get_settings()
        self._transport = transport
        self._sleep = sleep
        self._jitter = jitter

    async def chat(self, messages: list[dict[str, str]], temperature: float = 0.7) -> str:
        if not self.settings.deepseek_api_key:
            raise HTTPException(status_code=500, detail="DEEPSEEK_API_KEY is not configured.")

        url = f"{self.settings.deepseek_base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self.settings.deepseek_model,
            "messages": messages,
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.deepseek_api_key}",
            "Content-Type": "application/json",
        }

        timeout = httpx.Timeout(connect=10.0, read=180.0, write=30.0, pool=10.0)
        async with httpx.AsyncClient(timeout=timeout, transport=self._transport) as client:
            for attempt in range(self.MAX_RETRIES + 1):
                try:
                    response = await client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    break
                except httpx.HTTPStatusError as exc:
                    status_code = exc.response.status_code
                    if status_code in self.RETRYABLE_STATUSES and attempt < self.MAX_RETRIES:
                        await self._wait_before_retry(attempt, f"HTTP {status_code}")
                        continue
                    raise HTTPException(
                        status_code=502,
                        detail=f"DeepSeek API error: {status_code}",
                    ) from exc
                except httpx.TransportError as exc:
                    if attempt < self.MAX_RETRIES:
                        await self._wait_before_retry(attempt, type(exc).__name__)
                        continue
                    raise HTTPException(status_code=502, detail="Failed to call DeepSeek API.") from exc

        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise HTTPException(status_code=502, detail="DeepSeek API returned an unexpected response.") from exc

    async def _wait_before_retry(self, attempt: int, reason: str) -> None:
        delay = self.RETRY_BASE_SECONDS * (2**attempt) + self._jitter()
        logger.warning(
            "DeepSeek request failed with %s; retrying in %.2f seconds (attempt %s/%s).",
            reason,
            delay,
            attempt + 2,
            self.MAX_RETRIES + 1,
        )
        await self._sleep(delay)
