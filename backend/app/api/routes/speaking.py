import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.llm.base import LLMProvider
from app.providers.asr import ASRProvider
from app.providers.audio import normalize_to_pcm_wav
from app.providers.errors import ProviderError
from app.providers.factory import get_asr_provider, get_llm_provider, get_pronunciation_provider, get_tts_provider
from app.providers.pronunciation import PronunciationProvider
from app.providers.tts import TTSProvider
from app.schemas.agent import FeedbackResult, PartType
from app.schemas.speaking import SpeakingMode, TTSRequest, VoiceAnswerResponse, VoiceQuestionPayload
from app.schemas.mock_test import FinalizeFullMockTestRequest, MockAnswer, MockQuestion, SubmitFullMockTestResponse
from app.services.audio_asset_service import AudioAssetService, MIME_EXTENSIONS, normalize_mime_type
from app.services.full_mock_submission_service import FullMockSubmissionService
from app.services.practice_service import PracticeService
from app.services.speaking_scoring_service import SpeakingScoringService


router = APIRouter()
MAX_DURATIONS: dict[PartType, int] = {"part1": 180, "part2": 180, "part3": 180}


@router.post("/tts")
async def generate_examiner_speech(
    request: TTSRequest,
    provider: TTSProvider = Depends(get_tts_provider),
) -> Response:
    if request.voice not in get_settings().tts_allowed_voice_list:
        raise HTTPException(status_code=400, detail="Unsupported examiner voice.")
    try:
        audio, mime_type = await provider.synthesize(
            request.text.strip(), request.voice, request.accent, request.speed
        )
    except ProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    if not audio:
        raise HTTPException(status_code=502, detail="TTS provider returned empty audio.")
    return Response(content=audio, media_type=mime_type, headers={"Cache-Control": "no-store"})


@router.post("/voice-answer", response_model=VoiceAnswerResponse)
async def submit_voice_answer(
    audio: UploadFile = File(...),
    mode: SpeakingMode = Form(...),
    part_type: PartType = Form(...),
    question_id: str = Form(...),
    question_text: str = Form(...),
    question_payload: str = Form(...),
    duration: float = Form(...),
    mime_type: str = Form(""),
    db: Session = Depends(get_db),
    asr: ASRProvider = Depends(get_asr_provider),
    pronunciation: PronunciationProvider = Depends(get_pronunciation_provider),
    llm: LLMProvider = Depends(get_llm_provider),
) -> VoiceAnswerResponse:
    if not question_id.strip() or len(question_id) > 120:
        raise HTTPException(status_code=400, detail="Invalid question id.")
    if duration <= 0 or duration > MAX_DURATIONS[part_type] + 1:
        raise HTTPException(status_code=400, detail=f"Recording duration must be between 1 and {MAX_DURATIONS[part_type]} seconds.")
    try:
        payload = VoiceQuestionPayload.model_validate(json.loads(question_payload))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid question payload.") from exc
    if payload.part_type != part_type or payload.question.strip() != question_text.strip():
        raise HTTPException(status_code=400, detail="Question metadata does not match.")

    declared_mime = normalize_mime_type(audio.content_type or mime_type or "")
    fallback_mime = normalize_mime_type(mime_type)
    selected_mime = declared_mime if declared_mime in MIME_EXTENSIONS else fallback_mime
    if selected_mime not in MIME_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Unsupported audio format.")
    content = await audio.read(get_settings().max_audio_upload_bytes + 1)
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")
    if len(content) > get_settings().max_audio_upload_bytes:
        raise HTTPException(status_code=413, detail="Uploaded audio file is too large.")

    audio_service = AudioAssetService(db)
    try:
        asset = audio_service.create_pending(
            content=content,
            mime_type=selected_mime,
            duration_seconds=duration,
            question_id=question_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc

    normalized_path: Path | None = None
    try:
        normalized_path = await asyncio.to_thread(normalize_to_pcm_wav, audio_service.path_for(asset))
        asr_result = await asr.transcribe(normalized_path, "audio/wav")
        transcript = asr_result.transcript.strip()
        if not transcript:
            raise ProviderError("Speech recognition returned an empty transcript.")
        scoring_result, pronunciation_result = await asyncio.gather(
            SpeakingScoringService(llm).score(
                part_type=part_type,
                question=payload.to_examiner_question(),
                answer_text=transcript,
                mode=mode,
                answer_source="asr_transcript",
                strict=True,
            ),
            pronunciation.assess(normalized_path),
        )
        score, voice_feedback = scoring_result
        score.pronunciation = pronunciation_result.estimated_ielts_band
        score.pronunciation_assessment = pronunciation_result
        voice_feedback.pronunciation_note = pronunciation_result.message
        practice_id = None
        if mode == "single-practice":
            feedback = FeedbackResult(
                overall_band_score=score.overall,
                fluency_score=score.fluency_coherence,
                vocabulary_score=score.lexical_resource,
                grammar_score=score.grammatical_range_accuracy,
                pronunciation_score=score.pronunciation,
                pronunciation_note=voice_feedback.pronunciation_note,
                pronunciation_assessment=pronunciation_result,
                summary=voice_feedback.summary,
                strengths=voice_feedback.strengths,
                weaknesses=voice_feedback.weaknesses,
                corrections=voice_feedback.corrections,
                improved_answer=voice_feedback.improved_answer,
                action_suggestions=[voice_feedback.next_practice_suggestion] if voice_feedback.next_practice_suggestion else [],
                next_practice_suggestion=voice_feedback.next_practice_suggestion,
            )
            record = PracticeService(db).create_record(
                part_type=part_type,
                question=payload.to_examiner_question(),
                user_answer=transcript,
                feedback=feedback,
                answer_source="voice",
                transcript_text=transcript,
                audio_asset_id=asset.id,
            )
            practice_id = record.id
            audio_service.attach([asset.id], owner_type="practice", owner_id=record.id)
        return VoiceAnswerResponse(
            practice_id=practice_id,
            audio_asset_id=asset.id,
            audio_url=f"/api/speaking/audio/{asset.id}",
            transcript=transcript,
            asr_provider=asr_result.provider,
            is_mock_transcript=asr_result.is_mock,
            score=score,
            feedback=voice_feedback,
        )
    except ProviderError as exc:
        audio_service.delete_pending(asset.id)
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except HTTPException:
        audio_service.delete_pending(asset.id)
        raise
    except Exception as exc:
        audio_service.delete_pending(asset.id)
        raise HTTPException(status_code=502, detail="Transcription or scoring failed.") from exc
    finally:
        if normalized_path is not None:
            normalized_path.unlink(missing_ok=True)


@router.post("/mock-test/answer", response_model=MockAnswer)
async def score_full_mock_answer(
    audio: UploadFile = File(...),
    test_id: str = Form(...),
    question_id: str = Form(...),
    question_payload: str = Form(...),
    duration: float = Form(...),
    mime_type: str = Form(""),
    old_audio_asset_id: str | None = Form(None),
    db: Session = Depends(get_db),
    asr: ASRProvider = Depends(get_asr_provider),
    pronunciation: PronunciationProvider = Depends(get_pronunciation_provider),
    llm: LLMProvider = Depends(get_llm_provider),
) -> MockAnswer:
    if not test_id.strip() or len(test_id) > 120 or not question_id.strip() or len(question_id) > 120:
        raise HTTPException(status_code=400, detail="Invalid full mock test identity.")
    try:
        question = MockQuestion.model_validate(json.loads(question_payload))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid full mock question metadata.") from exc
    if duration <= 0 or duration > MAX_DURATIONS[question.part_type] + 1:
        raise HTTPException(
            status_code=400,
            detail=f"Recording duration must be between 1 and {MAX_DURATIONS[question.part_type]} seconds.",
        )
    return await FullMockSubmissionService(
        db,
        asr=asr,
        pronunciation=pronunciation,
        llm=llm,
    ).score_answer(
        test_id=test_id,
        question_id=question_id,
        question=question,
        duration=duration,
        fallback_mime=mime_type,
        upload=audio,
        old_audio_asset_id=old_audio_asset_id,
    )


@router.post("/mock-test/finalize", response_model=SubmitFullMockTestResponse)
def finalize_full_mock_test(
    request: FinalizeFullMockTestRequest,
    db: Session = Depends(get_db),
) -> SubmitFullMockTestResponse:
    return FullMockSubmissionService(db).finalize(request)


@router.get("/audio/{audio_id}")
def get_audio(audio_id: str, db: Session = Depends(get_db)) -> FileResponse:
    service = AudioAssetService(db)
    asset = service.get(audio_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Audio recording not found.")
    path = service.path_for(asset)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio recording file is missing.")
    return FileResponse(path, media_type=asset.mime_type, filename=asset.storage_name, content_disposition_type="inline")


@router.delete("/audio/{audio_id}", status_code=204)
def delete_pending_audio(audio_id: str, db: Session = Depends(get_db)) -> Response:
    if not AudioAssetService(db).delete_pending(audio_id):
        raise HTTPException(status_code=409, detail="Only pending audio recordings can be deleted.")
    return Response(status_code=204)
