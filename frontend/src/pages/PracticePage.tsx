import { useCallback, useEffect, useRef, useState } from "react";
import ArrowBackOutlinedIcon from "@mui/icons-material/ArrowBackOutlined";
import RefreshOutlinedIcon from "@mui/icons-material/RefreshOutlined";
import SendOutlinedIcon from "@mui/icons-material/SendOutlined";
import { Button, Stack, Typography } from "@mui/material";
import { startSectionPractice } from "../api/practices";
import { submitVoiceAnswer, voiceResultToFeedback } from "../api/speaking";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { SpokenQuestionCard } from "../components/SpokenQuestionCard";
import { VoiceAnswerRecorder, type VoiceAnswerRecorderHandle } from "../components/VoiceAnswerRecorder";
import { useExaminerVoice } from "../hooks/useExaminerVoice";
import type { ExaminerQuestion, FeedbackResult, PartType, SectionPracticeStart, VoiceAnswerValue } from "../types/practice";

const descriptions: Record<PartType, string> = {
  part1: "Short daily-life answers. Focus on natural responses with one or two details.",
  part2: "Cue card response. Build a structured story with clear sequencing and examples.",
  part3: "Abstract discussion. Expand your opinion with reasons, comparisons, and consequences."
};
const maxDurations: Record<PartType, number> = { part1: 180, part2: 180, part3: 180 };

export function PracticePage({
  partType,
  practiceGoal,
  initialSelection,
  onBack,
  onResult
}: {
  partType: PartType;
  practiceGoal: string;
  initialSelection?: SectionPracticeStart;
  onBack: () => void;
  onResult: (result: {
    practiceId: string;
    partType: PartType;
    question: ExaminerQuestion;
    userAnswer: string;
    feedback: FeedbackResult;
    audioUrl?: string;
    isMockTranscript?: boolean;
    practiceGoal: string;
  }) => void;
}) {
  const [question, setQuestion] = useState<ExaminerQuestion | null>(() => initialSelection ? sectionSelectionToQuestion(initialSelection) : null);
  const [questionId, setQuestionId] = useState(initialSelection?.selectionId ?? "");
  const [selectionMetadata, setSelectionMetadata] = useState(initialSelection?.metadata ?? null);
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
      const selection = await startSectionPractice(partType, practiceGoal);
      setQuestion(sectionSelectionToQuestion(selection));
      setQuestionId(selection.selectionId);
      setSelectionMetadata(selection.metadata);
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
        isMockTranscript: result.is_mock_transcript,
        practiceGoal
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to evaluate answer.");
    } finally {
      setSubmitting(false);
    }
  }

  useEffect(() => {
    if (!initialSelection) handleGenerate();
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
      {selectionMetadata?.fallbackUsed ? (
        <Typography color="warning.main" sx={{ fontSize: 14 }}>
          Semantic selection was unavailable, so an approved fallback question was selected.
        </Typography>
      ) : null}
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

export function sectionSelectionToQuestion(selection: SectionPracticeStart): ExaminerQuestion {
  const cue = selection.item.cueCard;
  return {
    part_type: selection.part,
    question: selection.item.text,
    cue_card: cue
      ? {
          topic: cue.topic,
          bullet_points: cue.bulletPoints,
          preparation_instruction: `You have ${cue.preparationTimeSeconds} seconds to prepare and up to ${cue.speakingTimeSeconds} seconds to speak.`,
          preparation_time_seconds: cue.preparationTimeSeconds,
          speaking_time_seconds: cue.speakingTimeSeconds
        }
      : null,
    bank_question_id: selection.item.id,
    topic: selection.item.topic,
    source: selection.item.source,
    difficulty: selection.item.difficulty
  };
}
