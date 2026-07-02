import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from app.config import Settings
from app.providers.asr import GeminiASRProvider
from app.providers.errors import ProviderError
from app.providers.tts import pcm_to_wav


class FakeGeminiModels:
    def __init__(self, text: str) -> None:
        self.text = text
        self.request = None

    async def generate_content(self, **kwargs):
        self.request = kwargs
        return SimpleNamespace(text=self.text)


class FakeGeminiError(Exception):
    def __init__(self, code: int) -> None:
        super().__init__(f"Gemini error {code}")
        self.code = code


class SequencedGeminiModels:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0

    async def generate_content(self, **kwargs):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(text=str(outcome))


class SequencedGeminiClient:
    def __init__(self, outcomes: list[object]) -> None:
        self.models = SequencedGeminiModels(outcomes)
        self.aio = SimpleNamespace(models=self.models)


class FakeGeminiClient:
    def __init__(self, text: str) -> None:
        self.models = FakeGeminiModels(text)
        self.aio = SimpleNamespace(models=self.models)


class GeminiASRProviderTests(unittest.TestCase):
    def test_reads_prepared_wav_and_returns_verbatim_transcript(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "answer.wav"
            source.write_bytes(pcm_to_wav(b"\x00\x00" * 16000, sample_rate=16000))
            client = FakeGeminiClient("Transcript: I, um, work as a developer.")
            settings = Settings(gemini_api_key="test-key", gemini_asr_model="gemini-test-model")
            provider = GeminiASRProvider(settings, client=client)

            result = asyncio.run(provider.transcribe(source, "audio/wav"))

            self.assertEqual(result.transcript, "I, um, work as a developer.")
            self.assertEqual(result.provider, "gemini")
            self.assertFalse(result.is_mock)
            self.assertEqual(client.models.request["model"], "gemini-test-model")
            audio_part = client.models.request["contents"][1]
            self.assertEqual(audio_part.inline_data.mime_type, "audio/wav")
            self.assertGreater(len(audio_part.inline_data.data), 44)

    def test_no_speech_marker_becomes_empty_transcript(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "answer.wav"
            source.write_bytes(pcm_to_wav(b"\x00\x00" * 8000, sample_rate=16000))
            provider = GeminiASRProvider(
                Settings(gemini_api_key="test-key"),
                client=FakeGeminiClient("[NO_SPEECH]"),
            )
            result = asyncio.run(provider.transcribe(source, "audio/wav"))
            self.assertEqual(result.transcript, "")

    def test_requires_gemini_api_key(self):
        with self.assertRaises(ProviderError):
            GeminiASRProvider(Settings(gemini_api_key=""))

    def test_retries_transient_503_with_exponential_backoff(self):
        delays: list[float] = []

        async def record_sleep(delay: float) -> None:
            delays.append(delay)

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "answer.wav"
            source.write_bytes(pcm_to_wav(b"\x00\x00" * 8000, sample_rate=16000))
            client = SequencedGeminiClient([FakeGeminiError(503), FakeGeminiError(503), "Recovered transcript"])
            provider = GeminiASRProvider(
                Settings(gemini_api_key="test-key"),
                client=client,
                sleep=record_sleep,
                jitter=lambda: 0.0,
            )

            result = asyncio.run(provider.transcribe(source, "audio/wav"))

        self.assertEqual(result.transcript, "Recovered transcript")
        self.assertEqual(client.models.calls, 3)
        self.assertEqual(delays, [2.0, 4.0])

    def test_stops_after_three_retries_and_preserves_503_message(self):
        delays: list[float] = []

        async def record_sleep(delay: float) -> None:
            delays.append(delay)

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "answer.wav"
            source.write_bytes(pcm_to_wav(b"\x00\x00" * 8000, sample_rate=16000))
            client = SequencedGeminiClient([FakeGeminiError(503) for _ in range(4)])
            provider = GeminiASRProvider(
                Settings(gemini_api_key="test-key"),
                client=client,
                sleep=record_sleep,
                jitter=lambda: 0.0,
            )

            with self.assertRaisesRegex(ProviderError, "temporarily busy") as context:
                asyncio.run(provider.transcribe(source, "audio/wav"))

        self.assertEqual(context.exception.status_code, 503)
        self.assertEqual(client.models.calls, 4)
        self.assertEqual(delays, [2.0, 4.0, 8.0])

    def test_does_not_retry_authentication_errors(self):
        async def fail_if_called(_: float) -> None:
            self.fail("Authentication errors must not be retried.")

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "answer.wav"
            source.write_bytes(pcm_to_wav(b"\x00\x00" * 8000, sample_rate=16000))
            client = SequencedGeminiClient([FakeGeminiError(401)])
            provider = GeminiASRProvider(
                Settings(gemini_api_key="test-key"),
                client=client,
                sleep=fail_if_called,
            )

            with self.assertRaisesRegex(ProviderError, "authentication failed"):
                asyncio.run(provider.transcribe(source, "audio/wav"))

        self.assertEqual(client.models.calls, 1)


if __name__ == "__main__":
    unittest.main()
