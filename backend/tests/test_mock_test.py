import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.mock_test import MockTestRecord
from app.schemas.mock_test import (
    EvaluateMockTestRequest,
    GenerateMockTestResponse,
    MockAnswer,
    MockQuestion,
    MockTestReport,
    validate_report_for_questions,
)
from app.services.mock_test_service import MockTestService


def question(part_type: str, index: int) -> dict:
    cue_card = None
    if part_type == "part2":
        cue_card = {
            "topic": "Describe a useful skill",
            "bullet_points": ["what it is", "when you learned it", "how you use it", "why it matters"],
            "preparation_instruction": "You have one minute to prepare.",
        }
    return {
        "part_type": part_type,
        "question_index": index,
        "question": f"{part_type} question {index}",
        "cue_card": cue_card,
    }


def questions() -> list[dict]:
    return [
        *[question("part1", index) for index in range(1, 5)],
        question("part2", 1),
        *[question("part3", index) for index in range(1, 4)],
    ]


def bank_questions() -> list[dict]:
    return [
        *[question("part1", index) for index in range(1, 7)],
        question("part2", 1),
        *[question("part3", index) for index in range(1, 5)],
    ]


def part_feedback(count: int) -> dict:
    return {
        "band_estimate": 6.5,
        "summary": "A useful summary.",
        "strengths": ["Clear ideas"],
        "weaknesses": ["More detail needed"],
        "question_analyses": [
            {
                "question_index": index,
                "band_estimate": 6.5,
                "feedback": "A specific analysis.",
                "strengths": ["Relevant"],
                "weaknesses": ["Limited range"],
                "improved_answer": "An improved answer.",
            }
            for index in range(1, count + 1)
        ],
    }


def report() -> MockTestReport:
    return MockTestReport.model_validate(
        {
            "overall_band_score": 6.5,
            "key_strengths": ["Coherent answers"],
            "key_weaknesses": ["Vocabulary range"],
            "action_plan": ["Practise topic vocabulary"],
            "part1_feedback": part_feedback(4),
            "part2_feedback": part_feedback(1),
            "part3_feedback": part_feedback(3),
        }
    )


class MockTestSchemaTests(unittest.TestCase):
    def test_accepts_exact_4_1_3_question_distribution(self):
        parsed = GenerateMockTestResponse.model_validate({"questions": questions()})
        self.assertEqual(len(parsed.questions), 8)

    def test_rejects_incomplete_question_distribution(self):
        with self.assertRaises(ValueError):
            GenerateMockTestResponse.model_validate({"questions": questions()[:-1]})

    def test_accepts_question_bank_6_1_4_distribution(self):
        parsed = EvaluateMockTestRequest.model_validate(
            {
                "answers": [
                    {
                        "part_type": item["part_type"],
                        "question_index": item["question_index"],
                        "question": item,
                        "answer_text": "A complete answer.",
                    }
                    for item in bank_questions()
                ]
            }
        )
        self.assertEqual(len(parsed.answers), 11)

    def test_answer_transport_fields_are_nullable(self):
        payload = [
            {
                "part_type": item["part_type"],
                "question_index": item["question_index"],
                "question": item,
                "answer_text": "A complete text answer.",
                "audio_url": None,
                "transcript_text": None,
            }
            for item in questions()
        ]
        parsed = EvaluateMockTestRequest.model_validate({"answers": payload})
        self.assertTrue(all(answer.audio_url is None and answer.transcript_text is None for answer in parsed.answers))

    def test_report_requires_analysis_for_every_question(self):
        invalid = report().model_dump()
        invalid["part1_feedback"]["question_analyses"].pop()
        parsed = MockTestReport.model_validate(invalid)
        with self.assertRaises(ValueError):
            validate_report_for_questions(parsed, [MockQuestion.model_validate(item) for item in questions()])


class MockTestServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine, tables=[MockTestRecord.__table__])
        self.session = sessionmaker(bind=self.engine)()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_round_trips_complete_mock_test(self):
        answer_models = [
            MockAnswer(
                part_type=item["part_type"],
                question_index=item["question_index"],
                question=MockQuestion.model_validate(item),
                answer_text="A complete text answer.",
                audio_url=None,
                transcript_text=None,
            )
            for item in questions()
        ]
        service = MockTestService(self.session)
        record = service.create_record(answer_models, report())
        detail = service.get_record(record.id)

        self.assertIsNotNone(detail)
        self.assertEqual(len(detail.answers), 8)
        self.assertEqual(detail.report.overall_band_score, 6.5)
        self.assertIsNone(detail.answers[0].audio_url)
        self.assertEqual(service.list_records()[0].id, record.id)


if __name__ == "__main__":
    unittest.main()
