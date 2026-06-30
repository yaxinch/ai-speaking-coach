from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import BACKEND_ROOT
from app.models.audio_asset import AudioAsset


MIME_EXTENSIONS = {
    "audio/webm": ".webm",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mp4": ".m4a",
    "audio/m4a": ".m4a",
    "audio/mpeg": ".mp3",
    "audio/ogg": ".ogg",
}


def normalize_mime_type(value: str) -> str:
    return value.split(";", 1)[0].strip().lower()


def audio_storage_path() -> Path:
    configured = Path(get_settings().audio_storage_dir)
    return configured if configured.is_absolute() else BACKEND_ROOT / configured


class AudioAssetService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.root = audio_storage_path()
        self.root.mkdir(parents=True, exist_ok=True)

    def create_pending(
        self,
        *,
        content: bytes,
        mime_type: str,
        duration_seconds: float,
        question_id: str,
    ) -> AudioAsset:
        normalized = normalize_mime_type(mime_type)
        extension = MIME_EXTENSIONS.get(normalized)
        if extension is None:
            raise ValueError("Unsupported audio format.")
        asset_id = str(uuid4())
        storage_name = f"{asset_id}{extension}"
        path = self.root / storage_name
        path.write_bytes(content)
        asset = AudioAsset(
            id=asset_id,
            storage_name=storage_name,
            mime_type=normalized,
            size_bytes=len(content),
            duration_seconds=duration_seconds,
            question_id=question_id,
        )
        try:
            self.db.add(asset)
            self.db.commit()
            self.db.refresh(asset)
        except Exception:
            self.db.rollback()
            path.unlink(missing_ok=True)
            raise
        return asset

    def get(self, asset_id: str) -> AudioAsset | None:
        return self.db.get(AudioAsset, asset_id)

    def path_for(self, asset: AudioAsset) -> Path:
        path = (self.root / asset.storage_name).resolve()
        if self.root.resolve() not in path.parents:
            raise ValueError("Invalid audio asset path.")
        return path

    def delete_pending(self, asset_id: str) -> bool:
        asset = self.get(asset_id)
        if asset is None or asset.status != "pending":
            return False
        self.path_for(asset).unlink(missing_ok=True)
        self.db.delete(asset)
        self.db.commit()
        return True

    def attach(self, asset_ids: list[str], *, owner_type: str, owner_id: str) -> None:
        unique_ids = list(dict.fromkeys(asset_ids))
        assets = self.db.query(AudioAsset).filter(AudioAsset.id.in_(unique_ids)).all() if unique_ids else []
        if len(assets) != len(unique_ids) or any(asset.status != "pending" for asset in assets):
            raise ValueError("One or more audio assets are missing or already attached.")
        for asset in assets:
            asset.status = "attached"
            asset.owner_type = owner_type
            asset.owner_id = owner_id
        self.db.commit()

    def cleanup_expired_pending(self) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=get_settings().audio_pending_ttl_hours)
        assets = self.db.query(AudioAsset).filter(AudioAsset.status == "pending", AudioAsset.created_at < cutoff).all()
        for asset in assets:
            self.path_for(asset).unlink(missing_ok=True)
            self.db.delete(asset)
        if assets:
            self.db.commit()
        return len(assets)
