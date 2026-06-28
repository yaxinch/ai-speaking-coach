import json

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.practice import PracticeRecord
from app.schemas.agent import ExaminerQuestion, FeedbackResult, PartType
from app.schemas.practice import PracticeDetail, PracticeSummary


class PracticeService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_record(
        self,
        part_type: PartType,
        question: ExaminerQuestion,
        user_answer: str,
        feedback: FeedbackResult,
    ) -> PracticeRecord:
        record = PracticeRecord(
            part_type=part_type,
            question_json=json.dumps(question.model_dump(), ensure_ascii=False),
            question_text=question.question,
            user_answer=user_answer,
            feedback_json=json.dumps(feedback.model_dump(), ensure_ascii=False),
            overall_band=feedback.overall_band_score,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_records(self) -> list[PracticeSummary]:
        records = self.db.query(PracticeRecord).order_by(desc(PracticeRecord.created_at)).all()
        return [
            PracticeSummary(
                id=record.id,
                part_type=record.part_type,
                question_text=record.question_text,
                overall_band=record.overall_band,
                created_at=record.created_at,
            )
            for record in records
        ]

    def get_record(self, record_id: str) -> PracticeDetail | None:
        record = self.db.get(PracticeRecord, record_id)
        if record is None:
            return None
        return PracticeDetail(
            id=record.id,
            part_type=record.part_type,
            question=ExaminerQuestion.model_validate(json.loads(record.question_json)),
            question_text=record.question_text,
            user_answer=record.user_answer,
            feedback=FeedbackResult.model_validate(json.loads(record.feedback_json)),
            overall_band=record.overall_band,
            created_at=record.created_at,
        )
