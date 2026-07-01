import asyncio
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.agents.mock_test_agent import MockTestAgent
from app.config import get_settings
from app.llm.base import LLMProvider
from app.providers.asr import ASRProvider
from app.providers.audio import normalize_to_pcm_wav
from app.providers.errors import ProviderError
from app.providers.pronunciation import PronunciationProvider
from app.schemas.agent import PronunciationAssessment
from app.schemas.mock_test import (
    FullMockSubmissionMetadata,
    MockAnswer,
    MockCriteriaScores,
    SubmitFullMockTestResponse,
)
from app.schemas.speaking import VoiceScore
from app.services.audio_asset_service import AudioAssetService, MIME_EXTENSIONS, normalize_mime_type
from app.services.mock_test_service import MockTestService


def round_half_band(value: float) -> float:
    rounded = (Decimal(str(value)) * 2).quantize(Decimal("1"), rounding=ROUND_HALF_UP) / 2
    return float(min(Decimal("9"), max(Decimal("0"), rounded)))


def average_band(values: list[float]) -> float | None:
    return round_half_band(sum(values) / len(values)) if values else None


class FullMockSubmissionService:
    def __init__(
        self,
        db: Session,
        *,
        asr: ASRProvider,
        pronunciation: PronunciationProvider,
        llm: LLMProvider,
    ) -> None:
        self.db = db
        self.asr = asr
        self.pronunciation = pronunciation
        self.agent = MockTestAgent(llm)
        self.audio_service = AudioAssetService(db)

    async def submit(
        self,
        metadata: FullMockSubmissionMetadata,
        uploads: list[UploadFile],
    ) -> SubmitFullMockTestResponse:
        asset_ids: list[str] = []
        normalized_paths: list[Path] = []
        answers: list[MockAnswer] = []
        try:
            for item, upload in zip(metadata.questions, uploads, strict=True):
                selected_mime = self._selected_mime(upload, item.mime_type)
                content = await upload.read(get_settings().max_audio_upload_bytes + 1)
                if not content:
                    raise HTTPException(status_code=400, detail=f"{self._label(item)} has an empty audio file.")
                if len(content) > get_settings().max_audio_upload_bytes:
                    raise HTTPException(status_code=413, detail=f"{self._label(item)} audio file is too large.")

                asset = self.audio_service.create_pending(
                    content=content,
                    mime_type=selected_mime,
                    duration_seconds=item.duration,
                    question_id=item.question_id,
                )
                asset_ids.append(asset.id)
                normalized_path = await asyncio.to_thread(normalize_to_pcm_wav, self.audio_service.path_for(asset))
                normalized_paths.append(normalized_path)

                try:
                    asr_result = await self.asr.transcribe(normalized_path, "audio/wav")
                except ProviderError as exc:
                    raise HTTPException(status_code=exc.status_code, detail=f"Transcription failed for {self._label(item)}: {exc.message}") from exc
                transcript = asr_result.transcript.strip()
                if not transcript:
                    raise HTTPException(status_code=502, detail=f"Transcription failed for {self._label(item)} because no speech was detected.")

                try:
                    pronunciation_result = await self.pronunciation.assess(normalized_path)
                except Exception:
                    pronunciation_result = PronunciationAssessment(
                        provider="none",
                        message="Pronunciation assessment is temporarily unavailable.",
                    )
                if not pronunciation_result.available:
                    pronunciation_result = pronunciation_result.model_copy(update={"provider": "none"})

                answers.append(
                    MockAnswer(
                        part_type=item.question.part_type,
                        question_index=item.question.question_index,
                        question=item.question,
                        answer_text=transcript,
                        audio_url=f"/api/speaking/audio/{asset.id}",
                        audio_asset_id=asset.id,
                        transcript_text=transcript,
                        voice_score=VoiceScore(
                            pronunciation=pronunciation_result.estimated_ielts_band,
                            pronunciation_assessment=pronunciation_result,
                        ),
                    )
                )

            llm_result = await self.agent.evaluate_full_mock(answers)
            scored_answers, report = self._merge_scores(answers, llm_result)
            record = MockTestService(self.db).create_record_and_attach(scored_answers, report, asset_ids)
            return SubmitFullMockTestResponse(mock_test_id=record.id, answers=scored_answers, report=report)
        except HTTPException:
            self.audio_service.delete_pending_many(asset_ids)
            raise
        except ProviderError as exc:
            self.audio_service.delete_pending_many(asset_ids)
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
        except Exception as exc:
            self.audio_service.delete_pending_many(asset_ids)
            raise HTTPException(status_code=502, detail="Full mock test transcription or scoring failed.") from exc
        finally:
            for path in normalized_paths:
                path.unlink(missing_ok=True)
            for upload in uploads:
                await upload.close()

    @staticmethod
    def _selected_mime(upload: UploadFile, fallback: str) -> str:
        declared = normalize_mime_type(upload.content_type or "")
        fallback_mime = normalize_mime_type(fallback)
        selected = declared if declared in MIME_EXTENSIONS else fallback_mime
        if selected not in MIME_EXTENSIONS:
            raise HTTPException(status_code=415, detail="Unsupported audio format.")
        return selected

    @staticmethod
    def _label(item) -> str:
        part = {"part1": "Part 1", "part2": "Part 2", "part3": "Part 3"}[item.question.part_type]
        return f"{part} Question {item.question.question_index}"

    @staticmethod
    def _merge_scores(answers, llm_result):
        score_by_key = {(item.part_type, item.question_index): item for item in llm_result.answer_scores}
        scored_answers: list[MockAnswer] = []
        for answer in answers:
            text_score = score_by_key[(answer.part_type, answer.question_index)]
            pronunciation = answer.voice_score.pronunciation if answer.voice_score else None
            criteria = [
                text_score.fluency_coherence,
                text_score.lexical_resource,
                text_score.grammatical_range_accuracy,
            ]
            if pronunciation is not None:
                criteria.append(pronunciation)
            score = VoiceScore(
                overall=average_band(criteria),
                fluency_coherence=text_score.fluency_coherence,
                lexical_resource=text_score.lexical_resource,
                grammatical_range_accuracy=text_score.grammatical_range_accuracy,
                pronunciation=pronunciation,
                pronunciation_assessment=answer.voice_score.pronunciation_assessment if answer.voice_score else None,
            )
            feedback = text_score.feedback.model_copy(
                update={
                    "pronunciation_note": (
                        score.pronunciation_assessment.message
                        if score.pronunciation_assessment
                        else "Pronunciation assessment is unavailable."
                    )
                }
            )
            scored_answers.append(answer.model_copy(update={"voice_score": score, "voice_feedback": feedback}))

        fluency = average_band([answer.voice_score.fluency_coherence for answer in scored_answers])
        lexical = average_band([answer.voice_score.lexical_resource for answer in scored_answers])
        grammar = average_band([answer.voice_score.grammatical_range_accuracy for answer in scored_answers])
        pronunciation_values = [
            answer.voice_score.pronunciation
            for answer in scored_answers
            if answer.voice_score.pronunciation is not None
        ]
        pronunciation = average_band(pronunciation_values)
        overall_values = [value for value in (fluency, lexical, grammar, pronunciation) if value is not None]

        report = llm_result.report.model_copy(deep=True)
        report.criteria_scores = MockCriteriaScores(
            fluency_coherence=fluency,
            lexical_resource=lexical,
            grammatical_range_accuracy=grammar,
            pronunciation=pronunciation,
        )
        report.overall_band_score = average_band(overall_values)
        for part_type in ("part1", "part2", "part3"):
            part_answers = [answer for answer in scored_answers if answer.part_type == part_type]
            feedback = getattr(report, f"{part_type}_feedback")
            feedback.band_estimate = average_band([answer.voice_score.overall for answer in part_answers])
            answer_by_index = {answer.question_index: answer for answer in part_answers}
            for analysis in feedback.question_analyses:
                analysis.band_estimate = answer_by_index[analysis.question_index].voice_score.overall
        if not report.next_practice_focus:
            report.next_practice_focus = list(report.action_plan)
        if not report.action_plan:
            report.action_plan = list(report.next_practice_focus)
        if not report.overall_feedback:
            report.overall_feedback = " ".join(
                summary for summary in (
                    report.part1_feedback.summary,
                    report.part2_feedback.summary,
                    report.part3_feedback.summary,
                ) if summary
            )
        return scored_answers, report
