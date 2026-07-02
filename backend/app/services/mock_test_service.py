import json

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.mock_test import MockTestRecord
from app.models.audio_asset import AudioAsset
from app.schemas.mock_test import MockAnswer, MockQuestion, MockTestDetail, MockTestReport, MockTestSummary


class MockTestService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_record(self, answers: list[MockAnswer], report: MockTestReport) -> MockTestRecord:
        questions = [answer.question for answer in answers]
        record = MockTestRecord(
            questions_json=json.dumps([item.model_dump() for item in questions], ensure_ascii=False),
            answers_json=json.dumps([item.model_dump() for item in answers], ensure_ascii=False),
            report_json=json.dumps(report.model_dump(), ensure_ascii=False),
            overall_band=report.overall_band_score,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def create_record_and_attach(
        self,
        answers: list[MockAnswer],
        report: MockTestReport,
        audio_asset_ids: list[str],
        *,
        submission_key: str | None = None,
    ) -> MockTestRecord:
        unique_ids = list(dict.fromkeys(audio_asset_ids))
        assets = self.db.query(AudioAsset).filter(AudioAsset.id.in_(unique_ids)).all() if unique_ids else []
        if len(assets) != len(unique_ids) or any(asset.status != "pending" for asset in assets):
            raise ValueError("One or more mock test recordings are unavailable.")
        record = MockTestRecord(
            questions_json=json.dumps([answer.question.model_dump() for answer in answers], ensure_ascii=False),
            answers_json=json.dumps([answer.model_dump() for answer in answers], ensure_ascii=False),
            report_json=json.dumps(report.model_dump(), ensure_ascii=False),
            overall_band=report.overall_band_score,
            submission_key=submission_key,
        )
        try:
            self.db.add(record)
            self.db.flush()
            for asset in assets:
                asset.status = "attached"
                asset.owner_type = "mock_test"
                asset.owner_id = record.id
            self.db.commit()
            self.db.refresh(record)
            return record
        except Exception:
            self.db.rollback()
            raise

    def get_record_by_submission_key(self, submission_key: str) -> MockTestDetail | None:
        record = self.db.query(MockTestRecord).filter(MockTestRecord.submission_key == submission_key).one_or_none()
        return self.get_record(record.id) if record is not None else None

    def list_records(self) -> list[MockTestSummary]:
        records = self.db.query(MockTestRecord).order_by(desc(MockTestRecord.created_at)).all()
        return [MockTestSummary(id=item.id, overall_band=item.overall_band, created_at=item.created_at) for item in records]

    def get_record(self, record_id: str) -> MockTestDetail | None:
        record = self.db.get(MockTestRecord, record_id)
        if record is None:
            return None
        return MockTestDetail(
            id=record.id,
            questions=[MockQuestion.model_validate(item) for item in json.loads(record.questions_json)],
            answers=[MockAnswer.model_validate(item) for item in json.loads(record.answers_json)],
            report=MockTestReport.model_validate(json.loads(record.report_json)),
            overall_band=record.overall_band,
            created_at=record.created_at,
        )

    def delete_record(self, record_id: str) -> bool:
        record = self.db.get(MockTestRecord, record_id)
        if record is None:
            return False
        from app.services.audio_asset_service import AudioAssetService

        audio_service = AudioAssetService(self.db)
        audio_service.delete_for_owner(owner_type="mock_test", owner_id=record_id, commit=False)
        self.db.delete(record)
        self.db.commit()
        return True
