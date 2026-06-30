from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import examiner, feedback, mock_tests, practices, speaking
from app.config import get_settings


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    from app.database import SessionLocal
    from app.services.audio_asset_service import AudioAssetService

    with SessionLocal() as db:
        AudioAssetService(db).cleanup_expired_pending()
    yield

app = FastAPI(title="AI Speaking Coach API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(examiner.router, prefix="/api/examiner", tags=["examiner"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["feedback"])
app.include_router(practices.router, prefix="/api/practices", tags=["practices"])
app.include_router(mock_tests.router, prefix="/api/mock-tests", tags=["mock-tests"])
app.include_router(speaking.router, prefix="/api/speaking", tags=["speaking"])
