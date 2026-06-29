import json

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.mock_test import MockTestRecord
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
