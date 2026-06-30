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


class FakeSignal:
    def __init__(self) -> None:
        self.callback = None

    def connect(self, callback) -> None:
        self.callback = callback


def continuous_speech_sdk(events: list[tuple[str, object]]):
    recognizers = []

    class SpeechConfig:
        def __init__(self, subscription, region) -> None:
            self.subscription = subscription
            self.region = region
            self.speech_recognition_language = ""
            self.output_format = None

    class AudioConfig:
        def __init__(self, filename) -> None:
            self.filename = filename

    class PronunciationAssessmentConfig:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        def enable_prosody_assessment(self) -> None:
            pass

        def apply_to(self, recognizer) -> None:
            pass

    class SpeechRecognizer:
        def __init__(self, speech_config, audio_config) -> None:
            self.recognized = FakeSignal()
            self.session_stopped = FakeSignal()
            self.canceled = FakeSignal()
            self.stopped = False
            recognizers.append(self)

        def start_continuous_recognition(self) -> None:
            for event_type, value in events:
                if event_type == "recognized" and self.recognized.callback:
                    result = SimpleNamespace(reason="recognized", properties=FakeProperties(value))
                    self.recognized.callback(SimpleNamespace(result=result))
                elif event_type == "canceled" and self.canceled.callback:
                    details = SimpleNamespace(reason=value)
                    self.canceled.callback(SimpleNamespace(result=SimpleNamespace(cancellation_details=details), cancellation_details=details))
                elif event_type == "stopped" and self.session_stopped.callback:
                    self.session_stopped.callback(SimpleNamespace())

        def stop_continuous_recognition(self) -> None:
            self.stopped = True

    sdk = SimpleNamespace(
        PropertyId=FakePropertyId,
        SpeechConfig=SpeechConfig,
        OutputFormat=SimpleNamespace(Detailed="detailed"),
        audio=SimpleNamespace(AudioConfig=AudioConfig),
        SpeechRecognizer=SpeechRecognizer,
        PronunciationAssessmentConfig=PronunciationAssessmentConfig,
        PronunciationAssessmentGradingSystem=SimpleNamespace(HundredMark="hundred"),
        PronunciationAssessmentGranularity=SimpleNamespace(Phoneme="phoneme"),
        ResultReason=SimpleNamespace(RecognizedSpeech="recognized"),
        recognizers=recognizers,
    )
    return sdk


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

    def test_continuous_recognition_aggregates_multiple_segments(self):
        first = {
            "Duration": 100,
            "NBest": [{"PronunciationAssessment": {"PronScore": 60, "AccuracyScore": 65, "FluencyScore": 55, "ProsodyScore": 50}, "Words": []}],
        }
        second = {
            "Duration": 300,
            "NBest": [{"PronunciationAssessment": {"PronScore": 80, "AccuracyScore": 85, "FluencyScore": 75, "ProsodyScore": 70}, "Words": []}],
        }
        sdk = continuous_speech_sdk([("recognized", first), ("recognized", second), ("stopped", None)])
        provider = AzurePronunciationProvider(Settings(azure_speech_key="key", azure_speech_region="region"), speechsdk=sdk)

        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "answer.wav"
            audio.write_bytes(b"RIFF")
            result = provider._assess_sync(audio)

        self.assertTrue(result.available)
        self.assertEqual(result.pron_score, 75.0)
        self.assertEqual(result.prosody_score, 65.0)
        self.assertTrue(sdk.recognizers[0].stopped)

    def test_continuous_recognition_reports_cancellation_without_raising(self):
        sdk = continuous_speech_sdk([("canceled", "network")])
        provider = AzurePronunciationProvider(Settings(azure_speech_key="key", azure_speech_region="region"), speechsdk=sdk)

        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "answer.wav"
            audio.write_bytes(b"RIFF")
            result = provider._assess_sync(audio)

        self.assertFalse(result.available)
        self.assertEqual(result.message, "Azure pronunciation assessment is temporarily unavailable.")

    def test_continuous_recognition_reports_timeout_and_stops_recognizer(self):
        sdk = continuous_speech_sdk([])
        provider = AzurePronunciationProvider(
            Settings(azure_speech_key="key", azure_speech_region="region", azure_pronunciation_timeout_seconds=0),
            speechsdk=sdk,
        )

        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "answer.wav"
            audio.write_bytes(b"RIFF")
            result = provider._assess_sync(audio)

        self.assertFalse(result.available)
        self.assertEqual(result.message, "Azure pronunciation assessment timed out.")
        self.assertTrue(sdk.recognizers[0].stopped)

    def test_continuous_recognition_reports_no_speech(self):
        sdk = continuous_speech_sdk([("stopped", None)])
        provider = AzurePronunciationProvider(Settings(azure_speech_key="key", azure_speech_region="region"), speechsdk=sdk)

        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "answer.wav"
            audio.write_bytes(b"RIFF")
            result = provider._assess_sync(audio)

        self.assertFalse(result.available)
        self.assertEqual(result.message, "No assessable English speech was detected.")

    def test_provider_exception_degrades_to_na(self):
        class BrokenSdk:
            class SpeechConfig:
                def __init__(self, **kwargs) -> None:
                    raise RuntimeError("secret upstream detail")

        provider = AzurePronunciationProvider(Settings(azure_speech_key="key", azure_speech_region="region"), speechsdk=BrokenSdk())
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "answer.wav"
            audio.write_bytes(b"RIFF")
            result = asyncio.run(provider.assess(audio))

        self.assertFalse(result.available)
        self.assertEqual(result.message, "Azure pronunciation assessment is temporarily unavailable.")


if __name__ == "__main__":
    unittest.main()
