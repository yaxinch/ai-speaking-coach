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
from app.providers.errors import ProviderError
from app.providers.factory import get_asr_provider, get_llm_provider, get_pronunciation_provider, get_tts_provider
from app.providers.pronunciation import DisabledPronunciationProvider, MockPronunciationProvider
from app.providers.tts import MockTTSProvider
from app.providers.tts import pcm_to_wav
from app.services.audio_asset_service import AudioAssetService
from tests.test_mock_test import questions, report


class FakeScoringLLM:
    full_mock_calls = 0

    async def chat(self, messages, temperature=0.7):
        if "as one coherent performance" in messages[-1]["content"]:
            type(self).full_mock_calls += 1
            return json.dumps(
                {
                    "answer_scores": [
                        {
                            "part_type": item["part_type"],
                            "question_index": item["question_index"],
                            "fluency_coherence": 6.0,
                            "lexical_resource": 7.0,
                            "grammatical_range_accuracy": 6.5,
                            "feedback": {
                                "summary": "A relevant answer.",
                                "strengths": ["Relevant"],
                                "weaknesses": ["Add detail"],
                                "corrections": [],
                                "improved_answer": "A stronger answer.",
                                "next_practice_suggestion": "Add examples.",
                            },
                        }
                        for item in questions()
                    ],
                    "report": report().model_dump(),
                }
            )
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


class FailingASRProvider:
    async def transcribe(self, audio_file_path, mime_type):
        raise ProviderError("ASR unavailable for test.", status_code=503)


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
        FakeScoringLLM.full_mock_calls = 0

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
        question = {
            "part_type": "part1",
            "question": "Do you work or study?",
            "cue_card": None,
            "bank_question_id": "bank-part1-1",
            "topic": "work",
            "source": "Reviewed practice source",
            "difficulty": "easy",
        }
        wav_audio = pcm_to_wav(b"\x00\x00" * 16000, sample_rate=16000)
        response = self.client.post(
            "/api/speaking/voice-answer",
            data={
                "mode": "single-practice",
                "part_type": "part1",
                "question_id": "part1-q1",
                "question_text": question["question"],
                "question_payload": json.dumps(question),
                "duration": "180",
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
        self.assertEqual(detail.json()["question"]["bank_question_id"], "bank-part1-1")
        self.assertEqual(detail.json()["question"]["source"], "Reviewed practice source")
        audio = self.client.get(body["audio_url"])
        self.assertEqual(audio.status_code, 200)
        self.assertEqual(audio.content, wav_audio)
        self.assertEqual(detail.json()["feedback"]["pronunciation_assessment"]["provider"], "mock")

        deleted = self.client.delete(f"/api/practices/{body['practice_id']}")
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(self.client.get(f"/api/practices/{body['practice_id']}").status_code, 404)
        self.assertEqual(self.client.get(body["audio_url"]).status_code, 404)
        with self.Session() as db:
            self.assertEqual(db.query(PracticeRecord).count(), 0)
            self.assertEqual(db.query(AudioAsset).count(), 0)

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

    def test_batch_full_mock_submission_scores_once_persists_and_deletes_audio(self):
        metadata = {
            "test_id": "session-1",
            "questions": [
                {
                    "index": index,
                    "question_id": f"session-1-{item['part_type']}-{item['question_index']}",
                    "question": item,
                    "duration": 1,
                    "mime_type": "audio/wav",
                }
                for index, item in enumerate(questions())
            ],
        }
        wav_audio = pcm_to_wav(b"\x00\x00" * 16000, sample_rate=16000)
        files = [
            (f"audio_{index}", (f"answer-{index}.wav", wav_audio, "audio/wav"))
            for index in range(len(questions()))
        ]
        response = self.client.post(
            "/api/speaking/mock-test/submit",
            data={"metadata": json.dumps(metadata)},
            files=files,
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(FakeScoringLLM.full_mock_calls, 1)
        self.assertEqual(len(body["answers"]), 8)
        self.assertEqual(body["answers"][0]["voice_score"]["overall"], 6.5)
        self.assertEqual(body["report"]["criteria_scores"]["pronunciation"], 7.0)
        mock_test_id = body["mock_test_id"]

        detail = self.client.get(f"/api/mock-tests/{mock_test_id}")
        self.assertEqual(detail.status_code, 200)
        audio_urls = [answer["audio_url"] for answer in detail.json()["answers"]]
        self.assertTrue(all(self.client.get(url).status_code == 200 for url in audio_urls))

        deleted = self.client.delete(f"/api/mock-tests/{mock_test_id}")
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(self.client.get(f"/api/mock-tests/{mock_test_id}").status_code, 404)
        self.assertTrue(all(self.client.get(url).status_code == 404 for url in audio_urls))
        with self.Session() as db:
            self.assertEqual(db.query(AudioAsset).count(), 0)
            self.assertEqual(db.query(MockTestRecord).count(), 0)

    def test_batch_full_mock_rejects_missing_audio_without_creating_assets(self):
        metadata = {
            "questions": [
                {
                    "index": index,
                    "question_id": f"missing-{index}",
                    "question": item,
                    "duration": 1,
                    "mime_type": "audio/wav",
                }
                for index, item in enumerate(questions())
            ]
        }
        response = self.client.post(
            "/api/speaking/mock-test/submit",
            data={"metadata": json.dumps(metadata)},
            files={"audio_0": ("answer.wav", pcm_to_wav(b"\x00\x00" * 16000), "audio/wav")},
        )
        self.assertEqual(response.status_code, 400)
        with self.Session() as db:
            self.assertEqual(db.query(AudioAsset).count(), 0)

    def test_batch_full_mock_asr_failure_identifies_question_and_cleans_pending_audio(self):
        app.dependency_overrides[get_asr_provider] = lambda: FailingASRProvider()
        metadata = {
            "questions": [
                {
                    "index": index,
                    "question_id": f"asr-failure-{index}",
                    "question": item,
                    "duration": 1,
                    "mime_type": "audio/wav",
                }
                for index, item in enumerate(questions())
            ]
        }
        wav_audio = pcm_to_wav(b"\x00\x00" * 16000, sample_rate=16000)
        response = self.client.post(
            "/api/speaking/mock-test/submit",
            data={"metadata": json.dumps(metadata)},
            files=[
                (f"audio_{index}", (f"answer-{index}.wav", wav_audio, "audio/wav"))
                for index in range(len(questions()))
            ],
        )
        self.assertEqual(response.status_code, 503)
        self.assertIn("Part 1 Question 1", response.json()["detail"])
        with self.Session() as db:
            self.assertEqual(db.query(AudioAsset).count(), 0)
            self.assertEqual(db.query(MockTestRecord).count(), 0)
        self.assertEqual(list(Path(self.temp.name).iterdir()), [])

    def test_batch_full_mock_pronunciation_failure_degrades_without_failing_test(self):
        app.dependency_overrides[get_pronunciation_provider] = lambda: DisabledPronunciationProvider("Azure unavailable.")
        metadata = {
            "questions": [
                {
                    "index": index,
                    "question_id": f"pronunciation-unavailable-{index}",
                    "question": item,
                    "duration": 1,
                    "mime_type": "audio/wav",
                }
                for index, item in enumerate(questions())
            ]
        }
        wav_audio = pcm_to_wav(b"\x00\x00" * 16000, sample_rate=16000)
        response = self.client.post(
            "/api/speaking/mock-test/submit",
            data={"metadata": json.dumps(metadata)},
            files=[
                (f"audio_{index}", (f"answer-{index}.wav", wav_audio, "audio/wav"))
                for index in range(len(questions()))
            ],
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertIsNone(body["report"]["criteria_scores"]["pronunciation"])
        self.assertTrue(all(answer["voice_score"]["pronunciation"] is None for answer in body["answers"]))
        self.assertTrue(all(answer["voice_score"]["pronunciation_assessment"]["provider"] == "none" for answer in body["answers"]))


if __name__ == "__main__":
    unittest.main()
