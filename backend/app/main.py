from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes import auth, examiner, feedback, mock_tests, practices, speaking
from app.auth import require_auth
from app.config import get_settings


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    from app.database import SessionLocal
    from app.services.audio_asset_service import AudioAssetService

    settings.validate_production_security()
    with SessionLocal() as db:
        AudioAssetService(db).cleanup_expired_pending()
    yield

app = FastAPI(title="AI Speaking Coach API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.require_session_secret(),
    session_cookie="speaking_coach_session",
    max_age=8 * 60 * 60,
    path="/",
    same_site="lax",
    https_only=settings.session_cookie_secure,
)

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


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
protected = [Depends(require_auth)]
app.include_router(examiner.router, prefix="/api/examiner", tags=["examiner"], dependencies=protected)
app.include_router(feedback.router, prefix="/api/feedback", tags=["feedback"], dependencies=protected)
app.include_router(practices.router, prefix="/api/practices", tags=["practices"], dependencies=protected)
app.include_router(mock_tests.router, prefix="/api/mock-tests", tags=["mock-tests"], dependencies=protected)
app.include_router(speaking.router, prefix="/api/speaking", tags=["speaking"], dependencies=protected)
