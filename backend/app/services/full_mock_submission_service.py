import asyncio
from collections import OrderedDict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.llm.base import LLMProvider
from app.models.audio_asset import AudioAsset
from app.providers.asr import ASRProvider
from app.providers.audio import normalize_to_pcm_wav
from app.providers.errors import ProviderError
from app.providers.pronunciation import PronunciationProvider
from app.schemas.agent import PronunciationAssessment
from app.schemas.mock_test import (
    FinalizeFullMockTestRequest,
    MockAnswer,
    MockCriteriaScores,
    MockPartPerformance,
    MockQuestion,
    MockTestReport,
    PartFeedback,
    QuestionAnalysis,
    RepeatedError,
    SubmitFullMockTestResponse,
)
from app.schemas.speaking import VoiceScore
from app.services.audio_asset_service import AudioAssetService, MIME_EXTENSIONS, normalize_mime_type
from app.services.mock_test_service import MockTestService
from app.services.speaking_scoring_service import SpeakingScoringService


def round_half_band(value: float) -> float:
    rounded = (Decimal(str(value)) * 2).quantize(Decimal("1"), rounding=ROUND_HALF_UP) / 2
    return float(min(Decimal("9"), max(Decimal("0"), rounded)))


def average_band(values: list[float]) -> float | None:
    return round_half_band(sum(values) / len(values)) if values else None


def unique_text(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = value.strip()
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result


class FullMockSubmissionService:
    def __init__(
        self,
        db: Session,
        *,
        asr: ASRProvider | None = None,
        pronunciation: PronunciationProvider | None = None,
        llm: LLMProvider | None = None,
    ) -> None:
        self.db = db
        self.asr = asr
        self.pronunciation = pronunciation
        self.llm = llm
        self.audio_service = AudioAssetService(db)

    async def score_answer(
        self,
        *,
        test_id: str,
        question_id: str,
        question: MockQuestion,
        duration: float,
        fallback_mime: str,
        upload: UploadFile,
        old_audio_asset_id: str | None = None,
    ) -> MockAnswer:
        if self.asr is None or self.pronunciation is None or self.llm is None:
            raise RuntimeError("Full mock answer scoring providers are not configured.")
        expected_question_id = self.question_id(test_id, question)
        if question_id != expected_question_id:
            raise HTTPException(status_code=400, detail="Full mock question identity does not match the test session.")
        if old_audio_asset_id:
            old_asset = self.audio_service.get(old_audio_asset_id)
            if old_asset is None or old_asset.status != "pending" or old_asset.question_id != expected_question_id:
                raise HTTPException(status_code=409, detail="The previous full mock recording is unavailable.")

        selected_mime = self._selected_mime(upload, fallback_mime)
        content = await upload.read(get_settings().max_audio_upload_bytes + 1)
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")
        if len(content) > get_settings().max_audio_upload_bytes:
            raise HTTPException(status_code=413, detail="Uploaded audio file is too large.")

        asset = self.audio_service.create_pending(
            content=content,
            mime_type=selected_mime,
            duration_seconds=duration,
            question_id=question_id,
        )
        normalized_path: Path | None = None
        try:
            normalized_path = await asyncio.to_thread(
                normalize_to_pcm_wav,
                self.audio_service.path_for(asset),
            )
            asr_result = await self.asr.transcribe(normalized_path, "audio/wav")
            transcript = asr_result.transcript.strip()
            if not transcript:
                raise ProviderError("Speech recognition returned an empty transcript.")

            scoring_result, pronunciation_result = await asyncio.gather(
                SpeakingScoringService(self.llm).score(
                    part_type=question.part_type,
                    question=question,
                    answer_text=transcript,
                    mode="mock-test",
                    answer_source="asr_transcript",
                    strict=True,
                ),
                self._assess_pronunciation(normalized_path),
            )
            score, feedback = scoring_result
            score.pronunciation = pronunciation_result.estimated_ielts_band
            score.pronunciation_assessment = pronunciation_result
            score.overall = average_band(
                [
                    value
                    for value in (
                        score.fluency_coherence,
                        score.lexical_resource,
                        score.grammatical_range_accuracy,
                        score.pronunciation,
                    )
                    if value is not None
                ]
            )
            feedback.pronunciation_note = pronunciation_result.message
            answer = MockAnswer(
                part_type=question.part_type,
                question_index=question.question_index,
                question=question,
                answer_text=transcript,
                audio_url=f"/api/speaking/audio/{asset.id}",
                audio_asset_id=asset.id,
                transcript_text=transcript,
                voice_score=score,
                voice_feedback=feedback,
            )
            if old_audio_asset_id:
                self.audio_service.delete_pending(old_audio_asset_id)
            return answer
        except ProviderError as exc:
            self.audio_service.delete_pending(asset.id)
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
        except HTTPException:
            self.audio_service.delete_pending(asset.id)
            raise
        except Exception as exc:
            self.audio_service.delete_pending(asset.id)
            raise HTTPException(status_code=502, detail="Full mock answer transcription or scoring failed.") from exc
        finally:
            if normalized_path is not None:
                normalized_path.unlink(missing_ok=True)
            await upload.close()

    def finalize(self, request: FinalizeFullMockTestRequest) -> SubmitFullMockTestResponse:
        mock_tests = MockTestService(self.db)
        existing = mock_tests.get_record_by_submission_key(request.test_id)
        if existing is not None:
            return SubmitFullMockTestResponse(
                mock_test_id=existing.id,
                answers=existing.answers,
                report=existing.report,
            )

        asset_ids = [answer.audio_asset_id for answer in request.answers]
        assets = self.db.query(AudioAsset).filter(AudioAsset.id.in_(asset_ids)).all()
        assets_by_id = {asset.id: asset for asset in assets}
        for answer in request.answers:
            asset = assets_by_id.get(answer.audio_asset_id)
            if (
                asset is None
                or asset.status != "pending"
                or asset.question_id != self.question_id(request.test_id, answer.question)
            ):
                raise HTTPException(status_code=409, detail="One or more full mock recordings are unavailable.")

        report = self.build_report(request.answers)
        try:
            record = mock_tests.create_record_and_attach(
                request.answers,
                report,
                asset_ids,
                submission_key=request.test_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except IntegrityError:
            existing = mock_tests.get_record_by_submission_key(request.test_id)
            if existing is None:
                raise
            return SubmitFullMockTestResponse(
                mock_test_id=existing.id,
                answers=existing.answers,
                report=existing.report,
            )
        return SubmitFullMockTestResponse(mock_test_id=record.id, answers=request.answers, report=report)

    @staticmethod
    def build_report(answers: list[MockAnswer]) -> MockTestReport:
        fluency = average_band([answer.voice_score.fluency_coherence for answer in answers])
        lexical = average_band([answer.voice_score.lexical_resource for answer in answers])
        grammar = average_band([answer.voice_score.grammatical_range_accuracy for answer in answers])
        pronunciation = average_band(
            [answer.voice_score.pronunciation for answer in answers if answer.voice_score.pronunciation is not None]
        )
        criteria = MockCriteriaScores(
            fluency_coherence=fluency,
            lexical_resource=lexical,
            grammatical_range_accuracy=grammar,
            pronunciation=pronunciation,
        )
        overall = average_band([value for value in criteria.model_dump().values() if value is not None])

        part_feedback: dict[str, PartFeedback] = {}
        performance: dict[str, str] = {}
        for part_type, label in (("part1", "Part 1"), ("part2", "Part 2"), ("part3", "Part 3")):
            part_answers = [answer for answer in answers if answer.part_type == part_type]
            band = average_band([answer.voice_score.overall for answer in part_answers])
            summaries = unique_text([answer.voice_feedback.summary for answer in part_answers])
            summary = f"{label} average band: {band:.1f}."
            if summaries:
                summary = f"{summary} {' '.join(summaries)}"
            feedback = PartFeedback(
                band_estimate=band,
                summary=summary,
                strengths=unique_text([item for answer in part_answers for item in answer.voice_feedback.strengths]),
                weaknesses=unique_text([item for answer in part_answers for item in answer.voice_feedback.weaknesses]),
                question_analyses=[
                    QuestionAnalysis(
                        question_index=answer.question_index,
                        band_estimate=answer.voice_score.overall,
                        feedback=answer.voice_feedback.summary,
                        strengths=answer.voice_feedback.strengths,
                        weaknesses=answer.voice_feedback.weaknesses,
                        improved_answer=answer.voice_feedback.improved_answer,
                    )
                    for answer in part_answers
                ],
            )
            part_feedback[part_type] = feedback
            performance[part_type] = summary

        strengths = unique_text([item for answer in answers for item in answer.voice_feedback.strengths])
        weaknesses = unique_text([item for answer in answers for item in answer.voice_feedback.weaknesses])
        suggestions = unique_text([answer.voice_feedback.next_practice_suggestion for answer in answers])
        repeated_errors = FullMockSubmissionService._aggregate_repeated_errors(answers)
        available = [
            ("Fluency and Coherence", fluency),
            ("Lexical Resource", lexical),
            ("Grammatical Range and Accuracy", grammar),
            ("Pronunciation", pronunciation),
        ]
        score_text = ", ".join(f"{label} {value:.1f}" for label, value in available if value is not None)
        overall_feedback = f"Overall band {overall:.1f}, calculated from the locally aggregated criterion scores: {score_text}."
        return MockTestReport(
            overall_band_score=overall,
            criteria_scores=criteria,
            overall_feedback=overall_feedback,
            key_strengths=strengths,
            key_weaknesses=weaknesses,
            action_plan=suggestions,
            next_practice_focus=suggestions,
            part_performance=MockPartPerformance.model_validate(performance),
            repeated_errors=repeated_errors,
            part1_feedback=part_feedback["part1"],
            part2_feedback=part_feedback["part2"],
            part3_feedback=part_feedback["part3"],
        )

    @staticmethod
    def _aggregate_repeated_errors(answers: list[MockAnswer]) -> list[RepeatedError]:
        grouped: OrderedDict[str, dict[str, object]] = OrderedDict()
        for answer in answers:
            for correction in answer.voice_feedback.corrections:
                key = correction.reason.strip().casefold() or "correction"
                group = grouped.setdefault(
                    key,
                    {"reason": correction.reason.strip() or "Correction", "examples": [], "corrected": correction.corrected},
                )
                examples = group["examples"]
                if correction.original.strip() and correction.original.strip() not in examples:
                    examples.append(correction.original.strip())
        return [
            RepeatedError(
                error_type=group["reason"],
                examples=group["examples"],
                suggestion=f"Use the corrected form: {group['corrected']}",
            )
            for group in grouped.values()
        ]

    async def _assess_pronunciation(self, path: Path) -> PronunciationAssessment:
        try:
            result = await self.pronunciation.assess(path)
        except Exception:
            result = PronunciationAssessment(
                provider="none",
                message="Pronunciation assessment is temporarily unavailable.",
            )
        return result if result.available else result.model_copy(update={"provider": "none"})

    @staticmethod
    def question_id(test_id: str, question: MockQuestion) -> str:
        return f"mock-{test_id}-{question.part_type}-{question.question_index}"

    @staticmethod
    def _selected_mime(upload: UploadFile, fallback: str) -> str:
        declared = normalize_mime_type(upload.content_type or "")
        fallback_mime = normalize_mime_type(fallback)
        selected = declared if declared in MIME_EXTENSIONS else fallback_mime
        if selected not in MIME_EXTENSIONS:
            raise HTTPException(status_code=415, detail="Unsupported audio format.")
        return selected
