import { useCallback, useEffect, useRef, useState } from "react";
import ArrowBackOutlinedIcon from "@mui/icons-material/ArrowBackOutlined";
import RefreshOutlinedIcon from "@mui/icons-material/RefreshOutlined";
import SendOutlinedIcon from "@mui/icons-material/SendOutlined";
import { Button, Stack, Typography } from "@mui/material";
import { generateQuestion } from "../api/examiner";
import { submitVoiceAnswer, voiceResultToFeedback } from "../api/speaking";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { SpokenQuestionCard } from "../components/SpokenQuestionCard";
import { VoiceAnswerRecorder, type VoiceAnswerRecorderHandle } from "../components/VoiceAnswerRecorder";
import { useExaminerVoice } from "../hooks/useExaminerVoice";
import type { ExaminerQuestion, FeedbackResult, PartType, VoiceAnswerValue } from "../types/practice";

const descriptions: Record<PartType, string> = {
  part1: "Short daily-life answers. Focus on natural responses with one or two details.",
  part2: "Cue card response. Build a structured story with clear sequencing and examples.",
  part3: "Abstract discussion. Expand your opinion with reasons, comparisons, and consequences."
};
const maxDurations: Record<PartType, number> = { part1: 300, part2: 300, part3: 300 };

export function PracticePage({
  partType,
  onBack,
  onResult
}: {
  partType: PartType;
  onBack: () => void;
  onResult: (result: {
    practiceId: string;
    partType: PartType;
    question: ExaminerQuestion;
    userAnswer: string;
    feedback: FeedbackResult;
    audioUrl?: string;
    isMockTranscript?: boolean;
  }) => void;
}) {
  const [question, setQuestion] = useState<ExaminerQuestion | null>(null);
  const [questionId, setQuestionId] = useState("");
  const [recording, setRecording] = useState<VoiceAnswerValue | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [loadingQuestion, setLoadingQuestion] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const recorderRef = useRef<VoiceAnswerRecorderHandle>(null);
  const stopUserPlayback = useCallback(() => recorderRef.current?.stopPlayback(), []);
  const examinerVoice = useExaminerVoice(stopUserPlayback);

  function clearRecording() {
    if (recording?.audioUrl) URL.revokeObjectURL(recording.audioUrl);
    setRecording(null);
  }

  async function handleGenerate() {
    setLoadingQuestion(true);
    setError("");
    examinerVoice.stop();
    if (questionId) examinerVoice.clear(questionId);
    clearRecording();
    try {
      setQuestion(await generateQuestion(partType));
      setQuestionId(`targeted-${partType}-${crypto.randomUUID()}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate question.");
    } finally {
      setLoadingQuestion(false);
    }
  }

  async function handleSubmit() {
    if (!question) {
      setError("Generate a question before submitting an answer.");
      return;
    }
    if (!recording?.audioBlob) {
      setError("Please record your answer before submitting.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      examinerVoice.stop();
      const result = await submitVoiceAnswer({ mode: "single-practice", partType, questionId, question, recording });
      if (recording.audioUrl) URL.revokeObjectURL(recording.audioUrl);
      onResult({
        practiceId: result.practice_id ?? "",
        partType,
        question,
        userAnswer: result.transcript,
        feedback: voiceResultToFeedback(result),
        audioUrl: result.audio_url,
        isMockTranscript: result.is_mock_transcript
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to evaluate answer.");
    } finally {
      setSubmitting(false);
    }
  }

  useEffect(() => {
    handleGenerate();
  }, [partType]);

  useEffect(() => () => {
    examinerVoice.stop();
    if (recording?.audioUrl) URL.revokeObjectURL(recording.audioUrl);
  }, [recording?.audioUrl]);

  return (
    <Stack spacing={2.75} sx={{ maxWidth: 1120 }}>
      <Button
        variant="outlined"
        startIcon={<ArrowBackOutlinedIcon />}
        onClick={onBack}
        disabled={submitting}
        sx={{ alignSelf: "flex-start" }}
      >
        Back to Part Selection
      </Button>
      <Stack
        direction={{ xs: "column", md: "row" }}
        spacing={2}
        sx={{ justifyContent: "space-between", alignItems: { xs: "stretch", md: "center" } }}
      >
        <Typography color="text.secondary">{descriptions[partType]}</Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshOutlinedIcon />}
          onClick={handleGenerate}
          disabled={loadingQuestion || submitting}
        >
          Regenerate Question
        </Button>
      </Stack>

      {error ? <ErrorState message={error} /> : null}
      {loadingQuestion ? <LoadingState label="Generating examiner question..." /> : null}
      {question && !loadingQuestion ? (
        <SpokenQuestionCard
          question={question}
          voiceState={examinerVoice.voices[questionId]}
          onPlay={() => examinerVoice.play(questionId, question.question)}
          disabled={submitting || isRecording}
        />
      ) : null}
      {question && !loadingQuestion ? (
        <VoiceAnswerRecorder
          ref={recorderRef}
          value={recording}
          onChange={setRecording}
          maxDuration={maxDurations[partType]}
          disabled={submitting}
          questionId={questionId}
          onRecordingStart={examinerVoice.stop}
          onPlaybackStart={examinerVoice.stop}
          onReRecord={() => setError("")}
          onRecordingStateChange={setIsRecording}
        />
      ) : null}
      <Button
        variant="contained"
        startIcon={<SendOutlinedIcon />}
        onClick={handleSubmit}
        disabled={submitting || loadingQuestion || isRecording || !recording?.audioBlob}
        sx={{ alignSelf: "flex-start" }}
      >
        {submitting ? "Transcribing and scoring your answer..." : "Submit Answer"}
      </Button>
    </Stack>
  );
}
