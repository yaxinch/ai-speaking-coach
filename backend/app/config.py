from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    database_url: str = "sqlite:///./data/app.db"
    cors_origins: str = "http://127.0.0.1:5180,http://localhost:5180"
    tts_provider: str = "mock"
    gemini_api_key: str = ""
    gemini_tts_model: str = "gemini-3.1-flash-tts-preview"
    gemini_tts_voice: str = "Kore"
    gemini_tts_mime_type: str = "audio/wav"
    tts_allowed_voices: str = "Kore"
    asr_provider: str = "mock"
    gemini_asr_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    gemini_embedding_dimensions: int = 768
    pronunciation_provider: str = "disabled"
    azure_speech_key: str = ""
    azure_speech_region: str = ""
    azure_speech_language: str = "en-US"
    azure_pronunciation_timeout_seconds: int = 330
    audio_storage_dir: str = "./data/audio"
    max_audio_upload_bytes: int = 25 * 1024 * 1024
    audio_pending_ttl_hours: int = 24

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def tts_allowed_voice_list(self) -> list[str]:
        return [voice.strip() for voice in self.tts_allowed_voices.split(",") if voice.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
