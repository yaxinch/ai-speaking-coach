import base64
import io
import math
import struct
import wave
from typing import Protocol

from google import genai
from google.genai import types

from app.config import Settings
from app.providers.errors import ProviderError


class TTSProvider(Protocol):
    async def synthesize(self, text: str, voice: str, accent: str, speed: float) -> tuple[bytes, str]: ...


def pcm_to_wav(pcm: bytes, *, sample_rate: int = 24000) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(sample_rate)
        writer.writeframes(pcm)
    return output.getvalue()


class MockTTSProvider:
    async def synthesize(self, text: str, voice: str, accent: str, speed: float) -> tuple[bytes, str]:
        sample_rate = 24000
        duration = 0.55
        frames = bytearray()
        for index in range(int(sample_rate * duration)):
            envelope = min(1.0, index / 600, (sample_rate * duration - index) / 600)
            sample = int(5000 * envelope * math.sin(2 * math.pi * 440 * index / sample_rate))
            frames.extend(struct.pack("<h", sample))
        return pcm_to_wav(bytes(frames), sample_rate=sample_rate), "audio/wav"


class GeminiTTSProvider:
    def __init__(self, settings: Settings) -> None:
        if not settings.gemini_api_key:
            raise ProviderError("Gemini TTS is not configured. Set GEMINI_API_KEY or use TTS_PROVIDER=mock.", status_code=503)
        self.settings = settings
        self.client = genai.Client(api_key=settings.gemini_api_key)

    async def synthesize(self, text: str, voice: str, accent: str, speed: float) -> tuple[bytes, str]:
        accent_label = "British" if accent == "british" else "American"
        prompt = (
            f"Read the following IELTS Speaking examiner question aloud in a natural, clear, and professional "
            f"{accent_label} English examiner voice. Keep the tone calm, neutral, and exam-like. "
            f"Speak at {speed:.2f}x normal pace. Do not add any extra words and do not read labels.\n\n{text}"
        )
        try:
            response = await self.client.aio.models.generate_content(
                model=self.settings.gemini_tts_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                        )
                    ),
                ),
            )
            data = response.candidates[0].content.parts[0].inline_data.data
        except Exception as exc:
            raise ProviderError("Failed to generate examiner voice.") from exc
        if isinstance(data, str):
            data = base64.b64decode(data)
        if not data:
            raise ProviderError("TTS provider returned empty audio.")
        return pcm_to_wav(bytes(data)), "audio/wav"
