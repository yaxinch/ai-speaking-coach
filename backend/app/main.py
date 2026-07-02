from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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


def frontend_file(full_path: str, dist_dir: Path) -> Path:
    """Resolve a frontend asset or fall back to index.html without escaping dist_dir."""
    if full_path == "api" or full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not Found")
    candidate = (dist_dir / full_path).resolve()
    if candidate != dist_dir and dist_dir not in candidate.parents:
        raise HTTPException(status_code=404, detail="Not Found")
    if candidate.is_file():
        return candidate
    index = dist_dir / "index.html"
    if index.is_file():
        return index
    raise HTTPException(status_code=404, detail="Frontend build is not available.")


@app.get("/{full_path:path}", include_in_schema=False)
def serve_frontend(full_path: str) -> FileResponse:
    return FileResponse(frontend_file(full_path, settings.frontend_dist_path))
