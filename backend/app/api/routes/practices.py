from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.practice import PracticeDetail, PracticeSummary
from app.services.practice_service import PracticeService

router = APIRouter()


@router.get("", response_model=list[PracticeSummary])
def list_practices(db: Session = Depends(get_db)) -> list[PracticeSummary]:
    return PracticeService(db).list_records()


@router.get("/{practice_id}", response_model=PracticeDetail)
def get_practice(practice_id: str, db: Session = Depends(get_db)) -> PracticeDetail:
    record = PracticeService(db).get_record(practice_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Practice record not found.")
    return record
