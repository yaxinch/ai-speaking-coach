from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.llm.base import LLMProvider
from app.providers.factory import get_llm_provider
from app.schemas.practice import (
    PracticeDetail,
    PracticeSummary,
    StartSectionPracticeRequest,
    StartSectionPracticeResponse,
)
from app.services.practice_service import PracticeService
from app.services.section_practice_composer_service import SectionPracticeComposerService, SectionPracticeUnavailable

router = APIRouter()


@router.post("/section/start", response_model=StartSectionPracticeResponse)
async def start_section_practice(
    request: StartSectionPracticeRequest,
    db: Session = Depends(get_db),
    llm: LLMProvider = Depends(get_llm_provider),
) -> StartSectionPracticeResponse:
    try:
        return await SectionPracticeComposerService(db, llm).start(request.part, request.practiceGoal)
    except SectionPracticeUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("", response_model=list[PracticeSummary])
def list_practices(db: Session = Depends(get_db)) -> list[PracticeSummary]:
    return PracticeService(db).list_records()


@router.get("/{practice_id}", response_model=PracticeDetail)
def get_practice(practice_id: str, db: Session = Depends(get_db)) -> PracticeDetail:
    record = PracticeService(db).get_record(practice_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Practice record not found.")
    return record
