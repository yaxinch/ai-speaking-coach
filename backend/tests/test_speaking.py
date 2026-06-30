import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.database import Base, get_db
from app.main import app
from app.models.audio_asset import AudioAsset
from app.models.mock_test import MockTestRecord
from app.models.practice import PracticeRecord
from app.providers.asr import MockASRProvider
from app.providers.factory import get_asr_provider, get_llm_provider, get_pronunciation_provider, get_tts_provider
from app.providers.pronunciation import DisabledPronunciationProvider, MockPronunciationProvider
from app.providers.tts import MockTTSProvider
from app.providers.tts import pcm_to_wav
from app.services.audio_asset_service import AudioAssetService
from tests.test_mock_test import questions, report


class FakeScoringLLM:
    async def chat(self, messages, temperature=0.7):
        if "Evaluate this complete text-based IELTS Speaking mock test" in messages[-1]["content"]:
            return report().model_dump_json()
        return json.dumps(
            {
                "overall_band_score": 6.5,
                "fluency_score": 6.5,
                "vocabulary_score": 7.0,
                "grammar_score": 6.0,
                "pronunciation_score": None,
                "pronunciation_note": "Pronunciation cannot be evaluated accurately from a transcript alone.",
                "summary": "A clear and relevant answer.",
                "strengths": ["Clear main idea"],
                "weaknesses": ["Add a specific example"],
                "corrections": [
                    {"original": "move into AI products", "corrected": "transition into AI product roles", "reason": "More precise wording"}
                ],
                "improved_answer": "I work as a front-end developer and I am preparing to transition into AI product roles.",
                "action_suggestions": ["Practise adding concrete examples."],
                "next_practice_suggestion": "Practise adding one concrete example to each answer.",
            }
        )


class SpeakingApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original_storage = get_settings().audio_storage_dir
        get_settings().audio_storage_dir = self.temp.name
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

        def override_db():
            with self.Session() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_llm_provider] = lambda: FakeScoringLLM()
        app.dependency_overrides[get_asr_provider] = lambda: MockASRProvider()
        app.dependency_overrides[get_pronunciation_provider] = lambda: MockPronunciationProvider()
        app.dependency_overrides[get_tts_provider] = lambda: MockTTSProvider()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self.engine.dispose()
        get_settings().audio_storage_dir = self.original_storage
        self.temp.cleanup()

    def test_mock_tts_returns_playable_wav(self):
        response = self.client.post(
            "/api/speaking/tts",
            json={"question_id": "part1-q1", "text": "Do you work or study?", "voice": "Kore", "accent": "british", "speed": 0.95},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "audio/wav")
        self.assertEqual(response.content[:4], b"RIFF")

    def test_voice_answer_persists_targeted_recording_and_transcript(self):
        question = {"part_type": "part1", "question": "Do you work or study?", "cue_card": None}
        wav_audio = pcm_to_wav(b"\x00\x00" * 16000, sample_rate=16000)
        response = self.client.post(
            "/api/speaking/voice-answer",
            data={
                "mode": "single-practice",
                "part_type": "part1",
                "question_id": "part1-q1",
                "question_text": question["question"],
                "question_payload": json.dumps(question),
                "duration": "300",
                "mime_type": "audio/wav",
            },
            files={"audio": ("part1-q1.wav", wav_audio, "audio/wav")},
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertTrue(body["practice_id"])
        self.assertTrue(body["is_mock_transcript"])
        self.assertEqual(body["score"]["pronunciation"], 7.0)
        self.assertEqual(body["score"]["pronunciation_assessment"]["pron_score"], 72.0)
        self.assertEqual(body["score"]["overall"], 6.5)

        detail = self.client.get(f"/api/practices/{body['practice_id']}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["answer_source"], "voice")
        self.assertEqual(detail.json()["audio_url"], body["audio_url"])
        audio = self.client.get(body["audio_url"])
        self.assertEqual(audio.status_code, 200)
        self.assertEqual(audio.content, wav_audio)
        self.assertEqual(detail.json()["feedback"]["pronunciation_assessment"]["provider"], "mock")

    def test_rejects_unsupported_audio_without_creating_asset(self):
        question = {"part_type": "part1", "question": "Do you work or study?", "cue_card": None}
        response = self.client.post(
            "/api/speaking/voice-answer",
            data={
                "mode": "mock-test",
                "part_type": "part1",
                "question_id": "part1-q1",
                "question_text": question["question"],
                "question_payload": json.dumps(question),
                "duration": "12",
                "mime_type": "text/plain",
            },
            files={"audio": ("answer.txt", b"not audio", "text/plain")},
        )
        self.assertEqual(response.status_code, 415)
        with self.Session() as db:
            self.assertEqual(db.query(AudioAsset).count(), 0)
        self.assertEqual(list(Path(self.temp.name).iterdir()), [])

    def test_pronunciation_failure_degrades_without_blocking_scoring(self):
        app.dependency_overrides[get_pronunciation_provider] = lambda: DisabledPronunciationProvider(
            "Azure pronunciation assessment is temporarily unavailable."
        )
        question = {"part_type": "part1", "question": "Do you work or study?", "cue_card": None}
        wav_audio = pcm_to_wav(b"\x00\x00" * 16000, sample_rate=16000)
        response = self.client.post(
            "/api/speaking/voice-answer",
            data={
                "mode": "single-practice",
                "part_type": "part1",
                "question_id": "part1-azure-unavailable",
                "question_text": question["question"],
                "question_payload": json.dumps(question),
                "duration": "1",
                "mime_type": "audio/wav",
            },
            files={"audio": ("answer.wav", wav_audio, "audio/wav")},
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["score"]["overall"], 6.5)
        self.assertIsNone(body["score"]["pronunciation"])
        self.assertFalse(body["score"]["pronunciation_assessment"]["available"])

    def test_final_mock_report_attaches_all_pending_audio(self):
        asset_ids = []
        with self.Session() as db:
            service = AudioAssetService(db)
            for index in range(8):
                asset = service.create_pending(
                    content=f"audio-{index}".encode(),
                    mime_type="audio/webm",
                    duration_seconds=10,
                    question_id=f"mock-q-{index}",
                )
                asset_ids.append(asset.id)
        payload = []
        for index, item in enumerate(questions()):
            payload.append(
                {
                    "part_type": item["part_type"],
                    "question_index": item["question_index"],
                    "question": item,
                    "answer_text": "A complete transcript.",
                    "audio_url": f"/api/speaking/audio/{asset_ids[index]}",
                    "audio_asset_id": asset_ids[index],
                    "transcript_text": "A complete transcript.",
                    "voice_score": {
                        "overall": 6.5,
                        "fluency_coherence": 6.5,
                        "lexical_resource": 6.5,
                        "grammatical_range_accuracy": 6.0,
                        "pronunciation": None,
                    },
                    "voice_feedback": {
                        "summary": "Clear answer.",
                        "strengths": ["Relevant"],
                        "weaknesses": ["Add detail"],
                        "corrections": [],
                        "improved_answer": "An improved answer.",
                        "next_practice_suggestion": "Add examples.",
                        "pronunciation_note": "Pronunciation cannot be evaluated accurately from a transcript alone.",
                    },
                }
            )
        response = self.client.post("/api/mock-tests/evaluate", json={"answers": payload})
        self.assertEqual(response.status_code, 200, response.text)
        mock_test_id = response.json()["mock_test_id"]
        with self.Session() as db:
            assets = db.query(AudioAsset).all()
            self.assertEqual(len(assets), 8)
            self.assertTrue(all(asset.status == "attached" and asset.owner_id == mock_test_id for asset in assets))


if __name__ == "__main__":
    unittest.main()
