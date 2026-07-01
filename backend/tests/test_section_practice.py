import json
import random
import unittest
from hashlib import sha256

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import practices
from app.database import Base, get_db
from app.models.practice import PracticeRecord
from app.providers.factory import get_llm_provider
from app.question_bank.embedding_service import EmbeddingUnavailable, encode_vector, vector_fingerprint
from app.question_bank.models import SpeakingQuestion
from app.question_bank.service import QuestionBankService
from app.services.section_practice_composer_service import SectionPracticeComposerService


class FakeEmbedding:
    model = "test-embedding"
    dimensions = 2

    def embed_query(self, _: str) -> list[float]:
        return [1.0, 0.0]


class UnavailableEmbedding(FakeEmbedding):
    def embed_query(self, _: str) -> list[float]:
        raise EmbeddingUnavailable("Embedding provider unavailable.")


class FakeLLM:
    def __init__(self, response: str = "{}"):
        self.response = response
        self.calls = []

    async def chat(self, messages, temperature=0.7):
        self.calls.append((messages, temperature))
        return self.response


def question(part: str, number: int, *, topic: str = "technology", approved: bool = True) -> SpeakingQuestion:
    text = f"{part} practice question {number}?"
    return SpeakingQuestion(
        id=f"{part}-{number}",
        part=part,
        question=text,
        cue_card_title=text if part == "part2" else None,
        cue_card_bullets=json.dumps(["what it is", "why it matters"]) if part == "part2" and number != 99 else None,
        topic=topic,
        difficulty="medium",
        source_name="Reviewed practice source",
        source_url="https://example.com/questions",
        source_type="education_site",
        source_format="webpage",
        confidence="medium",
        status="approved" if approved else "rejected",
        raw_text=text,
        content_hash=sha256(text.encode()).hexdigest(),
        embedding_text=text,
        embedding_model="test-embedding",
        embedding_vector_id=vector_fingerprint("test-embedding", text),
        embedding_vector=encode_vector([1.0, 0.0]),
        embedding_dimensions=2,
    )


class SectionPracticeServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine, tables=[SpeakingQuestion.__table__, PracticeRecord.__table__])
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.rows = [question(part, index) for part in ("part1", "part2", "part3") for index in (1, 2)]
        self.db.add_all([*self.rows, question("part1", 50, approved=False), question("part2", 99)])
        self.db.commit()
        self.bank = QuestionBankService(self.db, rng=random.Random(4))

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    async def test_default_selection_is_single_approved_item_and_skips_llm(self):
        llm = FakeLLM()
        service = SectionPracticeComposerService(self.db, llm, question_bank=self.bank)
        for part in ("part1", "part2", "part3"):
            with self.subTest(part=part):
                result = await service.start(part, "")
                self.assertEqual(result.part, part)
                self.assertEqual(result.mode, "default")
                self.assertFalse(result.metadata.retrievalUsed)
                self.assertEqual(result.item.type, "part2_cue_card" if part == "part2" else f"{part}_question")
                if part == "part2":
                    self.assertIsNotNone(result.item.cueCard)
        self.assertEqual(llm.calls, [])

    async def test_goal_selection_uses_only_candidate_id_and_backfills_data(self):
        selected = next(row for row in self.rows if row.part == "part3")
        llm = FakeLLM(json.dumps({"selectedId": selected.id}))
        result = await SectionPracticeComposerService(
            self.db,
            llm,
            embedding_service=FakeEmbedding(),
            question_bank=self.bank,
        ).start("part3", "technology")
        self.assertEqual(result.item.id, selected.id)
        self.assertEqual(result.item.text, selected.question)
        self.assertTrue(result.metadata.retrievalUsed)
        self.assertTrue(result.metadata.selectorUsed)
        self.assertFalse(result.metadata.fallbackUsed)
        self.assertEqual(llm.calls[0][1], 0.1)
        self.assertNotIn("part1-", str(llm.calls[0][0]))

    async def test_invalid_llm_id_falls_back_to_highest_similarity(self):
        result = await SectionPracticeComposerService(
            self.db,
            FakeLLM('{"selectedId":"part1-1"}'),
            embedding_service=FakeEmbedding(),
            question_bank=self.bank,
        ).start("part3", "technology")
        self.assertEqual(result.item.id, "part3-1")
        self.assertTrue(result.metadata.fallbackUsed)
        self.assertTrue(result.metadata.retrievalUsed)

    async def test_embedding_failure_uses_default_current_part(self):
        result = await SectionPracticeComposerService(
            self.db,
            FakeLLM(),
            embedding_service=UnavailableEmbedding(),
            question_bank=self.bank,
        ).start("part1", "environment")
        self.assertEqual(result.mode, "goal_based")
        self.assertEqual(result.part, "part1")
        self.assertFalse(result.metadata.retrievalUsed)
        self.assertTrue(result.metadata.fallbackUsed)


class SectionPracticeApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine, tables=[SpeakingQuestion.__table__, PracticeRecord.__table__])
        self.Session = sessionmaker(bind=self.engine)
        with self.Session() as db:
            db.add_all([question("part1", 1), question("part2", 1), question("part3", 1)])
            db.commit()
        app = FastAPI()
        app.include_router(practices.router, prefix="/api/practices")

        def db_override():
            with self.Session() as db:
                yield db

        app.dependency_overrides[get_db] = db_override
        app.dependency_overrides[get_llm_provider] = lambda: FakeLLM()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.engine.dispose()

    def test_static_start_route_returns_camel_case_contract(self):
        response = self.client.post("/api/practices/section/start", json={"part": "part2", "practiceGoal": ""})
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertTrue(body["selectionId"])
        self.assertEqual(body["item"]["type"], "part2_cue_card")
        self.assertEqual(body["item"]["cueCard"]["speakingTimeSeconds"], 120)
        self.assertFalse(body["metadata"]["retrievalUsed"])

    def test_goal_length_and_existing_dynamic_route_remain_valid(self):
        too_long = self.client.post(
            "/api/practices/section/start",
            json={"part": "part1", "practiceGoal": "x" * 301},
        )
        self.assertEqual(too_long.status_code, 422)
        missing = self.client.get("/api/practices/not-found")
        self.assertEqual(missing.status_code, 404)

    def test_missing_approved_part_returns_service_unavailable(self):
        with self.Session() as db:
            db.query(SpeakingQuestion).filter(SpeakingQuestion.part == "part3").delete()
            db.commit()
        response = self.client.post(
            "/api/practices/section/start",
            json={"part": "part3", "practiceGoal": ""},
        )
        self.assertEqual(response.status_code, 503)
        self.assertIn("No approved part3", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
