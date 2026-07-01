import { apiBlobRequest, apiEmptyRequest, apiRequest } from "./client";
import type { ExaminerQuestion, FeedbackResult, MockAnswer, MockTestReport, PartType, SubmitFullMockTestPayload, VoiceAnswerResult, VoiceAnswerValue } from "../types/practice";

function extensionForMime(mimeType: string): string {
  return mimeType.includes("wav") ? "wav" : mimeType.includes("mp4") ? "m4a" : mimeType.includes("mpeg") ? "mp3" : mimeType.includes("ogg") ? "ogg" : "webm";
}

export interface GenerateExaminerSpeechPayload {
  question_id: string;
  text: string;
  voice?: string;
  accent?: "british" | "american";
  speed?: number;
}

export function generateExaminerSpeech(payload: GenerateExaminerSpeechPayload): Promise<Blob> {
  return apiBlobRequest("/api/speaking/tts", { method: "POST", body: JSON.stringify(payload) });
}

export async function submitVoiceAnswer(payload: {
  mode: "single-practice" | "mock-test";
  partType: PartType;
  questionId: string;
  question: ExaminerQuestion;
  recording: VoiceAnswerValue;
}): Promise<VoiceAnswerResult> {
  if (!payload.recording.audioBlob) throw new Error("Please record your answer first.");
  const mimeType = payload.recording.mimeType || payload.recording.audioBlob.type || "audio/webm";
  const extension = extensionForMime(mimeType);
  const form = new FormData();
  form.append("audio", new File([payload.recording.audioBlob], `${payload.questionId}.${extension}`, { type: mimeType }));
  form.append("mode", payload.mode);
  form.append("part_type", payload.partType);
  form.append("question_id", payload.questionId);
  form.append("question_text", payload.question.question);
  form.append("question_payload", JSON.stringify(payload.question));
  form.append("duration", String(payload.recording.duration ?? 0));
  form.append("mime_type", mimeType);
  return apiRequest<VoiceAnswerResult>("/api/speaking/voice-answer", { method: "POST", body: form });
}

export async function submitFullMockTest(
  payload: SubmitFullMockTestPayload
): Promise<{ mock_test_id: string; answers: MockAnswer[]; report: MockTestReport }> {
  const form = new FormData();
  form.append("metadata", JSON.stringify({
    test_id: payload.testId,
    questions: payload.questions.map((item, index) => ({
      index,
      question_id: item.questionId,
      question: item.question,
      duration: item.duration,
      mime_type: item.mimeType || item.audioBlob.type || "audio/webm"
    }))
  }));
  payload.questions.forEach((item, index) => {
    const mimeType = item.mimeType || item.audioBlob.type || "audio/webm";
    form.append(
      `audio_${index}`,
      new File([item.audioBlob], `${item.questionId}.${extensionForMime(mimeType)}`, { type: mimeType })
    );
  });
  return apiRequest("/api/speaking/mock-test/submit", { method: "POST", body: form });
}

export function deletePendingAudio(audioAssetId: string): Promise<void> {
  return apiEmptyRequest(`/api/speaking/audio/${audioAssetId}`, { method: "DELETE" });
}

export function voiceResultToFeedback(result: VoiceAnswerResult): FeedbackResult {
  return {
    overall_band_score: result.score.overall,
    fluency_score: result.score.fluency_coherence,
    vocabulary_score: result.score.lexical_resource,
    grammar_score: result.score.grammatical_range_accuracy,
    pronunciation_score: result.score.pronunciation,
    pronunciation_note: result.feedback.pronunciation_note,
    pronunciation_assessment: result.score.pronunciation_assessment ?? null,
    summary: result.feedback.summary,
    strengths: result.feedback.strengths,
    weaknesses: result.feedback.weaknesses,
    corrections: result.feedback.corrections,
    improved_answer: result.feedback.improved_answer,
    action_suggestions: result.feedback.next_practice_suggestion ? [result.feedback.next_practice_suggestion] : [],
    next_practice_suggestion: result.feedback.next_practice_suggestion
  };
}
