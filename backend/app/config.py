from functools import lru_cache
from pathlib import Path
import re
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
BCRYPT_HASH_PATTERN = re.compile(r"^\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}$")


class Settings(BaseSettings):
    app_env: Literal["development", "production"] = "development"
    admin_username: str = ""
    admin_password_hash: str = ""
    session_secret_key: str = ""
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    database_url: str = "sqlite:///./data/app.db"
    cors_origins: str = (
        "http://127.0.0.1:5180,http://localhost:5180,"
        "http://127.0.0.1:5173,http://localhost:5173,"
        "http://127.0.0.1:3000,http://localhost:3000"
    )
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
    frontend_dist_dir: str = str(PROJECT_ROOT / "frontend" / "dist")

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

    @property
    def session_cookie_secure(self) -> bool:
        return self.app_env == "production"

    @property
    def frontend_dist_path(self) -> Path:
        return Path(self.frontend_dist_dir).resolve()

    def require_session_secret(self) -> str:
        secret = self.session_secret_key.strip()
        if not secret:
            raise RuntimeError("SESSION_SECRET_KEY is required.")
        return secret

    def validate_production_security(self) -> None:
        if self.app_env != "production":
            return
        errors: list[str] = []
        if not self.admin_username.strip():
            errors.append("ADMIN_USERNAME is required")
        if BCRYPT_HASH_PATTERN.fullmatch(self.admin_password_hash) is None:
            errors.append("ADMIN_PASSWORD_HASH must be a bcrypt hash")
        if len(self.session_secret_key) < 32:
            errors.append("SESSION_SECRET_KEY must contain at least 32 characters")
        if (
            not self.cors_origin_list
            or "*" in self.cors_origin_list
            or any(not origin.startswith("https://") for origin in self.cors_origin_list)
        ):
            errors.append("CORS_ORIGINS must contain explicit HTTPS origins")
        if errors:
            raise RuntimeError("Unsafe production configuration: " + "; ".join(errors) + ".")


@lru_cache
def get_settings() -> Settings:
    return Settings()
