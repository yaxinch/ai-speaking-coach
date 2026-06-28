from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import examiner, feedback, practices
from app.config import get_settings
from app.database import init_db


settings = get_settings()

app = FastAPI(title="AI Speaking Coach API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(examiner.router, prefix="/api/examiner", tags=["examiner"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["feedback"])
app.include_router(practices.router, prefix="/api/practices", tags=["practices"])
