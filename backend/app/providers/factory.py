from fastapi import HTTPException

from app.config import get_settings
from app.llm.base import LLMProvider
from app.llm.deepseek_provider import DeepSeekProvider
from app.providers.asr import ASRProvider, GeminiASRProvider, MockASRProvider
from app.providers.errors import ProviderError
from app.providers.pronunciation import (
    AzurePronunciationProvider,
    DisabledPronunciationProvider,
    MockPronunciationProvider,
    PronunciationProvider,
)
from app.providers.tts import GeminiTTSProvider, MockTTSProvider, TTSProvider


def get_llm_provider() -> LLMProvider:
    return DeepSeekProvider()


def get_tts_provider() -> TTSProvider:
    settings = get_settings()
    try:
        if settings.tts_provider == "mock":
            return MockTTSProvider()
        if settings.tts_provider == "gemini":
            return GeminiTTSProvider(settings)
    except ProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    raise HTTPException(status_code=503, detail=f"Unsupported TTS_PROVIDER: {settings.tts_provider}")


def get_asr_provider() -> ASRProvider:
    settings = get_settings()
    provider = settings.asr_provider
    if provider == "mock":
        return MockASRProvider()
    if provider == "gemini":
        try:
            return GeminiASRProvider(settings)
        except ProviderError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    if provider == "openai":
        raise HTTPException(status_code=503, detail="ASR_PROVIDER=openai is reserved but not implemented in this release.")
    raise HTTPException(status_code=503, detail=f"Unsupported ASR_PROVIDER: {provider}")


def get_pronunciation_provider() -> PronunciationProvider:
    settings = get_settings()
    provider = settings.pronunciation_provider.lower().strip()
    if provider == "mock":
        return MockPronunciationProvider()
    if provider in {"", "disabled", "none"}:
        return DisabledPronunciationProvider()
    if provider == "azure":
        if not settings.azure_speech_key or not settings.azure_speech_region:
            return DisabledPronunciationProvider(
                "Azure pronunciation assessment is not configured. Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION."
            )
        try:
            return AzurePronunciationProvider(settings)
        except Exception as exc:
            return DisabledPronunciationProvider(
                f"Azure pronunciation assessment could not be initialized ({type(exc).__name__})."
            )
    return DisabledPronunciationProvider(f"Unsupported PRONUNCIATION_PROVIDER: {provider}")
