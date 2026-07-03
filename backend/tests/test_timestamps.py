import unittest
from datetime import datetime, timedelta, timezone

from app.schemas.mock_test import MockTestSummary
from app.schemas.practice import PracticeSummary


class HistoryTimestampTests(unittest.TestCase):
    def test_naive_database_timestamp_is_serialized_as_utc(self):
        summary = PracticeSummary(
            id="practice-1",
            part_type="part1",
            question_text="Do you work or study?",
            overall_band=6.5,
            created_at=datetime(2026, 7, 3, 6, 14, 20),
        )

        self.assertEqual(summary.created_at.tzinfo, timezone.utc)
        self.assertIn('"created_at":"2026-07-03T06:14:20Z"', summary.model_dump_json())

    def test_aware_timestamp_is_converted_to_utc(self):
        summary = MockTestSummary(
            id="mock-1",
            overall_band=7.0,
            created_at=datetime(2026, 7, 3, 14, 14, 20, tzinfo=timezone(timedelta(hours=8))),
        )

        self.assertEqual(summary.created_at, datetime(2026, 7, 3, 6, 14, 20, tzinfo=timezone.utc))
        self.assertIn('"created_at":"2026-07-03T06:14:20Z"', summary.model_dump_json())


if __name__ == "__main__":
    unittest.main()
