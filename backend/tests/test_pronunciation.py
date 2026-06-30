import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from app.config import Settings
from app.providers.pronunciation import AzurePronunciationProvider, DisabledPronunciationProvider, estimated_ielts_band


class FakeProperties:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def get(self, property_id):
        return json.dumps(self.payload)


class FakePropertyId:
    SpeechServiceResponse_JsonResult = "json"


class FakeSpeechSdk:
    PropertyId = FakePropertyId


class PronunciationProviderTests(unittest.TestCase):
    def test_estimated_band_uses_half_band_and_caps_at_nine(self):
        self.assertEqual(estimated_ielts_band(72), 7.0)
        self.assertEqual(estimated_ielts_band(77), 7.5)
        self.assertEqual(estimated_ielts_band(99), 9.0)

    def test_parses_and_duration_weights_azure_segments(self):
        provider = AzurePronunciationProvider(Settings(azure_speech_key="key", azure_speech_region="region"), speechsdk=FakeSpeechSdk())
        first = SimpleNamespace(
            properties=FakeProperties(
                {
                    "Duration": 100,
                    "NBest": [{
                        "PronunciationAssessment": {"PronScore": 60, "AccuracyScore": 65, "FluencyScore": 55, "ProsodyScore": 50},
                        "Words": [{"Word": "first", "PronunciationAssessment": {"AccuracyScore": 40, "ErrorType": "None"}}],
                    }],
                }
            )
        )
        second = SimpleNamespace(
            properties=FakeProperties(
                {
                    "Duration": 300,
                    "NBest": [{
                        "PronunciationAssessment": {"PronScore": 80, "AccuracyScore": 85, "FluencyScore": 75, "ProsodyScore": 70},
                        "Words": [{"Word": "second", "PronunciationAssessment": {"AccuracyScore": 75, "ErrorType": "None"}}],
                    }],
                }
            )
        )
        segments = [provider._parse_segment(first), provider._parse_segment(second)]
        parsed = [item for item in segments if item is not None]
        self.assertEqual(provider._weighted(parsed, "pron_score"), 75.0)
        self.assertEqual(parsed[0].words[0].word, "first")

    def test_disabled_provider_returns_non_blocking_na(self):
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "answer.wav"
            audio.write_bytes(b"RIFF")
            result = asyncio.run(DisabledPronunciationProvider("not configured").assess(audio))
        self.assertFalse(result.available)
        self.assertIsNone(result.estimated_ielts_band)
        self.assertEqual(result.message, "not configured")


if __name__ == "__main__":
    unittest.main()
