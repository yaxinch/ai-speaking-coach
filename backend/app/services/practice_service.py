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
        answer_source: str = "text",
        transcript_text: str | None = None,
        audio_asset_id: str | None = None,
    ) -> PracticeRecord:
        record = PracticeRecord(
            part_type=part_type,
            question_json=json.dumps(question.model_dump(), ensure_ascii=False),
            question_text=question.question,
            user_answer=user_answer,
            answer_source=answer_source,
            transcript_text=transcript_text,
            audio_asset_id=audio_asset_id,
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
            answer_source=record.answer_source,
            transcript_text=record.transcript_text,
            audio_asset_id=record.audio_asset_id,
            audio_url=f"/api/speaking/audio/{record.audio_asset_id}" if record.audio_asset_id else None,
            overall_band=record.overall_band,
            created_at=record.created_at,
        )

    def delete_record(self, record_id: str) -> bool:
        record = self.db.get(PracticeRecord, record_id)
        if record is None:
            return False
        from app.services.audio_asset_service import AudioAssetService

        AudioAssetService(self.db).delete_for_owner(owner_type="practice", owner_id=record_id, commit=False)
        self.db.delete(record)
        self.db.commit()
        return True
