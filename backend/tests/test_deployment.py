import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from tests.auth_test_support import TEST_SESSION_SECRET  # noqa: F401
from app.database import Base
from app.main import frontend_file
from app.question_bank.models import SpeakingQuestion
from app.question_bank.repository import QuestionRepository
from app.question_bank.scripts.generate_embeddings import generate_embeddings
from app.question_bank.scripts.import_questions import load_import_records
from app.question_bank.service import prepare_questions


SEED_PATH = Path(__file__).resolve().parents[1] / "data" / "question_bank" / "seed" / "seed_questions.json"


class FakeEmbeddingService:
    model = "test-embedding-model"
    dimensions = 3

    def __init__(self):
        self.calls = 0

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        return [[1.0, 0.0, 0.0] for _ in texts]


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine, tables=[SpeakingQuestion.__table__])
        self.session_factory = sessionmaker(bind=self.engine)

    def tearDown(self):
        self.engine.dispose()

    def test_demo_seed_has_required_distribution_and_is_idempotent(self):
        prepared = prepare_questions(load_import_records(SEED_PATH))
        counts = {part: sum(row["part"] == part for row in prepared) for part in ("part1", "part2", "part3")}
        self.assertEqual(counts, {"part1": 30, "part2": 10, "part3": 20})
        self.assertTrue(all(row["status"] == "approved" for row in prepared))
        self.assertGreaterEqual(len({row["topic"] for row in prepared if row["part"] == "part1"}), 10)

        with self.session_factory() as db:
            repository = QuestionRepository(db)
            first = repository.bulk_insert(prepared)
            second = repository.bulk_insert(prepared)
        self.assertEqual((len(first[0]), first[1]), (60, 0))
        self.assertEqual((len(second[0]), second[1]), (0, 60))

    def test_embedding_bootstrap_skips_unchanged_rows(self):
        prepared = prepare_questions(load_import_records(SEED_PATH)[:2])
        with self.session_factory() as db:
            QuestionRepository(db).bulk_insert(prepared)
        embedding = FakeEmbeddingService()
        self.assertEqual(
            generate_embeddings(batch_size=50, embedding=embedding, session_factory=self.session_factory),
            (2, 0),
        )
        self.assertEqual(
            generate_embeddings(batch_size=50, embedding=embedding, session_factory=self.session_factory),
            (0, 2),
        )
        self.assertEqual(embedding.calls, 1)

    def test_frontend_file_serves_assets_and_spa_fallback_without_masking_api(self):
        with tempfile.TemporaryDirectory() as directory:
            dist = Path(directory)
            index = dist / "index.html"
            asset = dist / "asset.txt"
            index.write_text("app", encoding="utf-8")
            asset.write_text("asset", encoding="utf-8")
            self.assertEqual(frontend_file("asset.txt", dist), asset)
            self.assertEqual(frontend_file("practice/history", dist), index)
            with self.assertRaisesRegex(Exception, "404"):
                frontend_file("api/not-a-route", dist)
            with self.assertRaisesRegex(Exception, "404"):
                frontend_file("../outside.txt", dist)


if __name__ == "__main__":
    unittest.main()
