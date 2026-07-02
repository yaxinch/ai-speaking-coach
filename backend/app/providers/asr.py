import asyncio
import logging
import random
import re
from pathlib import Path
from typing import Any, Protocol

from google import genai
from google.genai import types
from app.config import Settings
from app.providers.errors import ProviderError


logger = logging.getLogger(__name__)


class ASRResult:
    def __init__(self, transcript: str, provider: str, is_mock: bool = False) -> None:
        self.transcript = transcript
        self.provider = provider
        self.is_mock = is_mock


class ASRProvider(Protocol):
    async def transcribe(self, audio_file_path: Path, mime_type: str) -> ASRResult: ...


class MockASRProvider:
    async def transcribe(self, audio_file_path: Path, mime_type: str) -> ASRResult:
        if not audio_file_path.exists() or audio_file_path.stat().st_size == 0:
            raise ProviderError("Speech recognition failed because the audio file is empty.", status_code=400)
        return ASRResult(
            "I currently work as a front-end developer, but I am also learning product management because I want to move into AI products.",
            provider="mock",
            is_mock=True,
        )


class GeminiASRProvider:
    MAX_INLINE_AUDIO_BYTES = 19 * 1024 * 1024
    MAX_RETRIES = 3
    RETRY_BASE_SECONDS = 2.0

    def __init__(
        self,
        settings: Settings,
        *,
        client: Any | None = None,
        sleep=asyncio.sleep,
        jitter=random.random,
    ) -> None:
        if not settings.gemini_api_key:
            raise ProviderError(
                "Gemini ASR is not configured. Set GEMINI_API_KEY or use ASR_PROVIDER=mock.",
                status_code=503,
            )
        self.settings = settings
        self.client = client or genai.Client(api_key=settings.gemini_api_key)
        self._sleep = sleep
        self._jitter = jitter

    @staticmethod
    def _clean_transcript(value: str) -> str:
        transcript = value.strip().strip("`").strip()
        transcript = re.sub(r"^transcript\s*:\s*", "", transcript, flags=re.IGNORECASE).strip()
        if transcript.upper() in {"[NO_SPEECH]", "NO_SPEECH"}:
            return ""
        return transcript

    async def transcribe(self, audio_file_path: Path, mime_type: str) -> ASRResult:
        if not audio_file_path.exists() or audio_file_path.stat().st_size == 0:
            raise ProviderError("Speech recognition failed because the audio file is empty.", status_code=400)
        audio_bytes = await asyncio.to_thread(audio_file_path.read_bytes)
        if len(audio_bytes) > self.MAX_INLINE_AUDIO_BYTES:
            raise ProviderError("The normalized audio is too large for Gemini inline transcription.", status_code=413)
        prompt = (
            "Transcribe the spoken English in this IELTS Speaking answer. Return only the verbatim transcript, "
            "with no title, timestamps, markdown, explanation, correction, or translation. Preserve filler words, "
            "false starts, repetitions, and grammatical errors because the transcript will be scored as spoken. "
            "If there is no intelligible speech, return exactly [NO_SPEECH]."
        )

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.settings.gemini_asr_model,
                    contents=[prompt, types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav")],
                    config=types.GenerateContentConfig(temperature=0),
                )
                transcript = self._clean_transcript(response.text or "")
                return ASRResult(transcript, provider="gemini", is_mock=False)
            except ProviderError:
                raise
            except Exception as exc:
                status_code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
                if status_code in {429, 503} and attempt < self.MAX_RETRIES:
                    delay = self.RETRY_BASE_SECONDS * (2**attempt) + self._jitter()
                    logger.warning(
                        "Gemini ASR returned retryable status %s; retrying in %.2f seconds (attempt %s/%s).",
                        status_code,
                        delay,
                        attempt + 2,
                        self.MAX_RETRIES + 1,
                    )
                    await self._sleep(delay)
                    continue
                if status_code == 429:
                    raise ProviderError("Gemini speech recognition rate limit reached. Please try again shortly.", status_code=429) from exc
                if status_code == 503:
                    raise ProviderError("Gemini speech recognition is temporarily busy. Please try again shortly.", status_code=503) from exc
                if status_code in {401, 403}:
                    raise ProviderError("Gemini speech recognition authentication failed. Check GEMINI_API_KEY.", status_code=503) from exc
                raise ProviderError("Gemini speech recognition failed. Please try again.") from exc
