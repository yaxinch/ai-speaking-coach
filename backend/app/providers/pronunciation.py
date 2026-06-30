import asyncio
import json
import logging
import threading
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Protocol

from app.config import Settings
from app.schemas.agent import PronunciationAssessment, WeakPronunciationWord


logger = logging.getLogger(__name__)


def estimated_ielts_band(pron_score: float) -> float:
    raw_band = Decimal(str(pron_score)) / Decimal("10")
    rounded = (raw_band * 2).quantize(Decimal("1"), rounding=ROUND_HALF_UP) / 2
    return float(min(Decimal("9"), max(Decimal("0"), rounded)))


class PronunciationProvider(Protocol):
    async def assess(self, audio_file_path: Path) -> PronunciationAssessment: ...


class DisabledPronunciationProvider:
    def __init__(self, message: str = "Pronunciation assessment is not configured.") -> None:
        self.message = message

    async def assess(self, audio_file_path: Path) -> PronunciationAssessment:
        return PronunciationAssessment(provider="disabled", message=self.message)


class MockPronunciationProvider:
    async def assess(self, audio_file_path: Path) -> PronunciationAssessment:
        if not audio_file_path.exists() or audio_file_path.stat().st_size == 0:
            return PronunciationAssessment(provider="mock", is_mock=True, message="The audio file is empty.")
        return PronunciationAssessment(
            available=True,
            provider="mock",
            is_mock=True,
            pron_score=72.0,
            estimated_ielts_band=7.0,
            accuracy_score=74.0,
            fluency_score=70.0,
            prosody_score=71.0,
            weak_words=[WeakPronunciationWord(word="example", accuracy_score=58.0)],
            message="Mock pronunciation assessment; no Azure request was made.",
        )


@dataclass
class _Segment:
    duration: float
    pron_score: float
    accuracy_score: float
    fluency_score: float
    prosody_score: float | None
    words: list[WeakPronunciationWord]


class AzurePronunciationProvider:
    def __init__(self, settings: Settings, *, speechsdk: Any | None = None) -> None:
        self.settings = settings
        if speechsdk is None:
            import azure.cognitiveservices.speech as speechsdk_module

            speechsdk = speechsdk_module
        self.speechsdk = speechsdk

    @staticmethod
    def _score(value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _parse_segment(self, result: Any) -> _Segment | None:
        sdk = self.speechsdk
        raw_json = result.properties.get(sdk.PropertyId.SpeechServiceResponse_JsonResult)
        if not raw_json:
            return None
        payload = json.loads(raw_json)
        nbest = (payload.get("NBest") or [{}])[0]
        assessment = nbest.get("PronunciationAssessment") or {}
        pron_score = self._score(assessment.get("PronScore"))
        accuracy = self._score(assessment.get("AccuracyScore"))
        fluency = self._score(assessment.get("FluencyScore"))
        prosody = self._score(assessment.get("ProsodyScore"))
        if pron_score is None or accuracy is None or fluency is None:
            return None
        words: list[WeakPronunciationWord] = []
        for item in nbest.get("Words") or []:
            word_assessment = item.get("PronunciationAssessment") or {}
            word_accuracy = self._score(word_assessment.get("AccuracyScore"))
            word = str(item.get("Word") or "").strip()
            if word and word_accuracy is not None:
                words.append(
                    WeakPronunciationWord(
                        word=word,
                        accuracy_score=word_accuracy,
                        error_type=word_assessment.get("ErrorType"),
                    )
                )
        duration_ticks = self._score(payload.get("Duration")) or self._score(getattr(result, "duration", 0)) or 1
        return _Segment(
            duration=max(duration_ticks, 1),
            pron_score=pron_score,
            accuracy_score=accuracy,
            fluency_score=fluency,
            prosody_score=prosody,
            words=words,
        )

    @staticmethod
    def _weighted(segments: list[_Segment], field: str) -> float | None:
        pairs = [(getattr(item, field), item.duration) for item in segments if getattr(item, field) is not None]
        if not pairs:
            return None
        total_weight = sum(weight for _, weight in pairs)
        return round(sum(value * weight for value, weight in pairs) / total_weight, 1)

    def _assess_sync(self, audio_file_path: Path) -> PronunciationAssessment:
        sdk = self.speechsdk
        speech_config = sdk.SpeechConfig(
            subscription=self.settings.azure_speech_key,
            region=self.settings.azure_speech_region,
        )
        speech_config.speech_recognition_language = self.settings.azure_speech_language
        speech_config.output_format = sdk.OutputFormat.Detailed
        audio_config = sdk.audio.AudioConfig(filename=str(audio_file_path))
        recognizer = sdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
        pronunciation_config = sdk.PronunciationAssessmentConfig(
            reference_text="",
            grading_system=sdk.PronunciationAssessmentGradingSystem.HundredMark,
            granularity=sdk.PronunciationAssessmentGranularity.Phoneme,
            enable_miscue=False,
        )
        pronunciation_config.enable_prosody_assessment()
        pronunciation_config.apply_to(recognizer)

        segments: list[_Segment] = []
        finished = threading.Event()
        cancellation: list[str] = []

        def recognized(evt: Any) -> None:
            if evt.result.reason == sdk.ResultReason.RecognizedSpeech:
                try:
                    segment = self._parse_segment(evt.result)
                    if segment is not None:
                        segments.append(segment)
                except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                    logger.warning("Azure pronunciation returned an unreadable result segment.")

        def canceled(evt: Any) -> None:
            details = getattr(evt, "cancellation_details", None) or getattr(evt.result, "cancellation_details", None)
            cancellation.append(str(getattr(details, "reason", "Azure speech recognition was canceled.")))
            finished.set()

        recognizer.recognized.connect(recognized)
        recognizer.session_stopped.connect(lambda evt: finished.set())
        recognizer.canceled.connect(canceled)
        recognizer.start_continuous_recognition()
        completed = finished.wait(timeout=self.settings.azure_pronunciation_timeout_seconds)
        recognizer.stop_continuous_recognition()

        if not completed:
            return PronunciationAssessment(provider="azure", message="Azure pronunciation assessment timed out.")
        if not segments:
            message = "No assessable English speech was detected."
            if cancellation:
                message = "Azure pronunciation assessment is temporarily unavailable."
            return PronunciationAssessment(provider="azure", message=message)

        pron_score = self._weighted(segments, "pron_score")
        all_words = [word for segment in segments for word in segment.words]
        weak_words = sorted(all_words, key=lambda item: item.accuracy_score)[:10]
        return PronunciationAssessment(
            available=True,
            provider="azure",
            pron_score=pron_score,
            estimated_ielts_band=estimated_ielts_band(pron_score or 0),
            accuracy_score=self._weighted(segments, "accuracy_score"),
            fluency_score=self._weighted(segments, "fluency_score"),
            prosody_score=self._weighted(segments, "prosody_score"),
            weak_words=weak_words,
            message="Estimated IELTS band is a heuristic derived from Azure PronScore, not an official IELTS conversion.",
        )

    async def assess(self, audio_file_path: Path) -> PronunciationAssessment:
        if not audio_file_path.exists() or audio_file_path.stat().st_size == 0:
            return PronunciationAssessment(provider="azure", message="The audio file is empty.")
        try:
            return await asyncio.to_thread(self._assess_sync, audio_file_path)
        except Exception as exc:
            logger.warning("Azure pronunciation assessment failed: %s", type(exc).__name__)
            return PronunciationAssessment(
                provider="azure",
                message="Azure pronunciation assessment is temporarily unavailable.",
            )
