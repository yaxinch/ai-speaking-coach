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


if __name__ == "__main__":
    unittest.main()
