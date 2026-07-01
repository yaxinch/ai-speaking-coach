import json
import random
import unittest
from hashlib import sha256

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.question_bank.embedding_service import EmbeddingUnavailable, decode_vector, encode_vector, vector_fingerprint
from app.question_bank.models import SpeakingQuestion
from app.question_bank.service import QuestionBankService
from app.question_bank.vector_search import VectorSearchService
from app.services.mock_session_composer_service import MockSessionComposerService


class FakeEmbeddingService:
    model = "test-embedding"
    dimensions = 2

    def embed_query(self, _: str) -> list[float]:
        return [1.0, 0.0]


class UnavailableEmbeddingService(FakeEmbeddingService):
    def embed_query(self, _: str) -> list[float]:
        raise EmbeddingUnavailable("Embedding index unavailable.")


class FakeLLM:
    def __init__(self, response: str):
        self.response = response
        self.calls = []

    async def chat(self, messages, temperature=0.7):
        self.calls.append((messages, temperature))
        return self.response


def make_question(part: str, number: int, topic: str, *, vector=(1.0, 0.0)) -> SpeakingQuestion:
    question = f"{part} {topic} question {number}?"
    cue_title = question if part == "part2" else None
    cue_bullets = json.dumps(["what it is", "why it matters"]) if part == "part2" else None
    content_hash = sha256(question.encode()).hexdigest()
    return SpeakingQuestion(
        id=f"{part}-{topic}-{number}",
        part=part,
        question=question,
        cue_card_title=cue_title,
        cue_card_bullets=cue_bullets,
        topic=topic,
        difficulty="medium",
        source_name="Reviewed practice source",
        source_url="https://example.com/questions",
        source_type="education_site",
        source_format="webpage",
        confidence="medium",
        status="approved",
        raw_text=question,
        embedding_text=question,
        embedding_model="test-embedding",
        embedding_vector_id=vector_fingerprint("test-embedding", question),
        embedding_vector=encode_vector(vector),
        embedding_dimensions=2,
        content_hash=content_hash,
    )


class MockSessionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine, tables=[SpeakingQuestion.__table__])
        self.session = sessionmaker(bind=self.engine)()
        self.part1_a = [make_question("part1", index, "technology") for index in range(1, 4)]
        self.part1_b = [make_question("part1", index, "work") for index in range(1, 4)]
        self.part2 = make_question("part2", 1, "technology")
        self.part3 = [make_question("part3", index, "technology") for index in range(1, 5)]
        rejected = make_question("part3", 99, "technology")
        rejected.status = "rejected"
        self.session.add_all([*self.part1_a, *self.part1_b, self.part2, *self.part3, rejected])
        self.session.commit()
        self.bank = QuestionBankService(self.session, rng=random.Random(3))

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    async def test_default_session_uses_only_approved_questions_and_fixed_profile(self):
        service = MockSessionComposerService(self.session, FakeLLM("{}"), question_bank=self.bank)
        result = await service.start("")
        self.assertEqual(result.mode, "default")
        self.assertFalse(result.metadata.retrievalUsed)
        self.assertEqual([len(group.questions) for group in result.parts.part1.topics], [3, 3])
        self.assertEqual(len(result.parts.part3.questions), 4)
        self.assertEqual(result.parts.part2.cueCard.speakingTimeSeconds, 120)
        self.assertNotIn("part3-technology-99", [item.id for item in result.parts.part3.questions])

    async def test_goal_session_validates_ids_and_backfills_question_data(self):
        selection = {
            "part1": {
                "topics": [
                    {"topic": "technology", "questionIds": [row.id for row in self.part1_a]},
                    {"topic": "work", "questionIds": [row.id for row in self.part1_b]},
                ]
            },
            "part2": {"cueCardId": self.part2.id},
            "part3": {"questionIds": [row.id for row in self.part3]},
        }
        llm = FakeLLM(json.dumps(selection))
        service = MockSessionComposerService(
            self.session,
            llm,
            embedding_service=FakeEmbeddingService(),
            question_bank=self.bank,
        )
        result = await service.start("technology")
        self.assertEqual(result.mode, "goal_based")
        self.assertTrue(result.metadata.retrievalUsed)
        self.assertTrue(result.metadata.composerUsed)
        self.assertFalse(result.metadata.fallbackUsed)
        self.assertEqual(result.parts.part2.cueCard.source, "Reviewed practice source")
        self.assertEqual(len(llm.calls), 1)

    async def test_invalid_llm_selection_falls_back_to_retrieval_candidates(self):
        service = MockSessionComposerService(
            self.session,
            FakeLLM('{"part1": {"topics": []}}'),
            embedding_service=FakeEmbeddingService(),
            question_bank=self.bank,
        )
        result = await service.start("technology")
        self.assertTrue(result.metadata.retrievalUsed)
        self.assertTrue(result.metadata.fallbackUsed)
        self.assertEqual(len(result.parts.part3.questions), 4)

    async def test_embedding_failure_returns_goal_based_default_fallback(self):
        service = MockSessionComposerService(
            self.session,
            FakeLLM("{}"),
            embedding_service=UnavailableEmbeddingService(),
            question_bank=self.bank,
        )
        result = await service.start("environment")
        self.assertEqual(result.mode, "goal_based")
        self.assertFalse(result.metadata.retrievalUsed)
        self.assertTrue(result.metadata.fallbackUsed)
        self.assertIn("unavailable", result.metadata.fallbackReason.lower())

    def test_vector_storage_and_part_filtered_cosine_search(self):
        encoded = encode_vector([3.0, 4.0])
        self.assertAlmostEqual(decode_vector(encoded, 2)[0], 0.6, places=5)
        results = VectorSearchService(self.session, model="test-embedding", dimensions=2).search(
            [1.0, 0.0], part="part2", top_k=5
        )
        self.assertEqual([item.question.id for item in results], [self.part2.id])


if __name__ == "__main__":
    unittest.main()
