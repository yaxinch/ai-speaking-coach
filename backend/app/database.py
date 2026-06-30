from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
BACKEND_ROOT = Path(__file__).resolve().parents[1]

if settings.database_url.startswith("sqlite:///./"):
    relative_db_path = Path(settings.database_url.replace("sqlite:///./", "", 1))
    db_path = BACKEND_ROOT / relative_db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    database_url = f"sqlite:///{db_path.as_posix()}"
else:
    database_url = settings.database_url

engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models.audio_asset import AudioAsset
    from app.models.mock_test import MockTestRecord
    from app.models.practice import PracticeRecord

    _ = (PracticeRecord, MockTestRecord, AudioAsset)
    Base.metadata.create_all(bind=engine)
