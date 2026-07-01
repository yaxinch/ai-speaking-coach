import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ArrowBackOutlinedIcon from "@mui/icons-material/ArrowBackOutlined";
import ArrowForwardOutlinedIcon from "@mui/icons-material/ArrowForwardOutlined";
import { Alert, Box, Button, Chip, LinearProgress, Stack, TextField, Typography } from "@mui/material";
import { evaluateMockTest, startMockTest } from "../api/mockTests";
import { deletePendingAudio, submitVoiceAnswer } from "../api/speaking";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { SpokenQuestionCard } from "../components/SpokenQuestionCard";
import { VoiceAnswerRecorder, type VoiceAnswerRecorderHandle } from "../components/VoiceAnswerRecorder";
import { useExaminerVoice } from "../hooks/useExaminerVoice";
import type { MockAnswer, MockQuestion, MockSession, MockTestReport, PartType, VoiceAnswerResult, VoiceAnswerValue } from "../types/practice";

const order: Record<PartType, number> = { part1: 1, part2: 2, part3: 3 };
const labels: Record<PartType, string> = { part1: "Part 1", part2: "Part 2", part3: "Part 3" };
const maxDurations: Record<PartType, number> = { part1: 180, part2: 180, part3: 180 };

type AnswerStatus = "empty" | "recorded" | "submitting" | "completed" | "failed";
interface MockVoiceState {
  recording?: VoiceAnswerValue | null;
  result?: VoiceAnswerResult;
  status: AnswerStatus;
  errorMessage?: string;
}

export function FullMockTestPage({
  onResult
}: {
  onResult: (result: { mockTestId: string; answers: MockAnswer[]; report: MockTestReport }) => void;
}) {
  const [questions, setQuestions] = useState<MockQuestion[]>([]);
  const [practiceGoal, setPracticeGoal] = useState("");
  const [sessionMetadata, setSessionMetadata] = useState<MockSession["metadata"] | null>(null);
  const [answers, setAnswers] = useState<Record<string, MockVoiceState>>({});
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState("");
  const sessionIdRef = useRef("");
  const recorderRef = useRef<VoiceAnswerRecorderHandle>(null);
  const localUrlsRef = useRef(new Set<string>());
  const stopUserPlayback = useCallback(() => recorderRef.current?.stopPlayback(), []);
  const examinerVoice = useExaminerVoice(stopUserPlayback);

  const sortedQuestions = useMemo(
    () => [...questions].sort((a, b) => order[a.part_type] - order[b.part_type] || a.question_index - b.question_index),
    [questions]
  );
  const current = sortedQuestions[currentIndex];
  const keyFor = (question: MockQuestion) => `${question.part_type}-${question.question_index}`;
  const questionIdFor = (question: MockQuestion) => `mock-${sessionIdRef.current}-${keyFor(question)}`;
  const currentKey = current ? keyFor(current) : "";
  const currentAnswer = answers[currentKey] ?? { status: "empty" as const };
  const completed = sortedQuestions.filter((question) => answers[keyFor(question)]?.status === "completed").length;

  useEffect(() => () => {
    examinerVoice.stop();
    localUrlsRef.current.forEach(URL.revokeObjectURL);
    localUrlsRef.current.clear();
  }, []);

  function revokeLocalUrl(url?: string) {
    if (url && localUrlsRef.current.has(url)) {
      URL.revokeObjectURL(url);
      localUrlsRef.current.delete(url);
    }
  }

  async function handleStart() {
    setLoading(true);
    setError("");
    examinerVoice.stop();
    localUrlsRef.current.forEach(URL.revokeObjectURL);
    localUrlsRef.current.clear();
    try {
      const result = await startMockTest(practiceGoal);
      sessionIdRef.current = result.sessionId;
      setQuestions(flattenMockSession(result));
      setSessionMetadata(result.metadata);
      setAnswers({});
      setCurrentIndex(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate a full mock test.");
    } finally {
      setLoading(false);
    }
  }

  function handleRecordingChange(value: VoiceAnswerValue | null) {
    if (!current) return;
    const previous = answers[currentKey];
    if (previous?.recording?.audioUrl && previous.recording.audioUrl !== value?.audioUrl) revokeLocalUrl(previous.recording.audioUrl);
    if (value?.audioUrl?.startsWith("blob:")) localUrlsRef.current.add(value.audioUrl);
    setAnswers((existing) => ({
      ...existing,
      [currentKey]: {
        recording: value,
        status: value?.audioBlob ? "recorded" : "empty"
      }
    }));
    setError("");
  }

  async function handleReRecord() {
    const priorAsset = currentAnswer.result?.audio_asset_id;
    if (priorAsset) {
      try {
        await deletePendingAudio(priorAsset);
      } catch {
        // The 24-hour pending cleanup remains the fallback if this best-effort delete fails.
      }
    }
  }

  async function submitCurrent(): Promise<VoiceAnswerResult | null> {
    if (!current || !currentAnswer.recording?.audioBlob) {
      setError("Please record your answer before moving to the next question.");
      return null;
    }
    if (currentAnswer.status === "completed" && currentAnswer.result) return currentAnswer.result;
    setSubmitting(true);
    setError("");
    setAnswers((existing) => ({ ...existing, [currentKey]: { ...existing[currentKey], status: "submitting", errorMessage: undefined } }));
    try {
      const result = await submitVoiceAnswer({
        mode: "mock-test",
        partType: current.part_type,
        questionId: questionIdFor(current),
        question: current,
        recording: currentAnswer.recording
      });
      revokeLocalUrl(currentAnswer.recording.audioUrl);
      setAnswers((existing) => ({
        ...existing,
        [currentKey]: {
          recording: { ...currentAnswer.recording, audioUrl: result.audio_url },
          result,
          status: "completed"
        }
      }));
      return result;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to transcribe and score this answer.";
      setAnswers((existing) => ({ ...existing, [currentKey]: { ...existing[currentKey], status: "failed", errorMessage: message } }));
      setError(message);
      return null;
    } finally {
      setSubmitting(false);
    }
  }

  async function handleNext() {
    examinerVoice.stop();
    recorderRef.current?.stopPlayback();
    if (await submitCurrent()) setCurrentIndex((value) => value + 1);
  }

  function handlePrevious() {
    examinerVoice.stop();
    recorderRef.current?.stopPlayback();
    setError("");
    setCurrentIndex((value) => Math.max(0, value - 1));
  }

  async function handleFinish() {
    const currentResult = await submitCurrent();
    if (!currentResult) return;
    const latestAnswers: Record<string, MockVoiceState> = {
      ...answers,
      [currentKey]: {
        ...currentAnswer,
        result: currentResult,
        status: "completed",
        recording: currentAnswer.recording
          ? { ...currentAnswer.recording, audioUrl: currentResult.audio_url }
          : currentAnswer.recording
      }
    };
    const incomplete = sortedQuestions.filter((question) => latestAnswers[keyFor(question)]?.status !== "completed");
    if (incomplete.length) {
      setError(incomplete.map((question) => `${labels[question.part_type]} Question ${question.question_index} is not completed.`).join(" "));
      return;
    }
    const payload: MockAnswer[] = sortedQuestions.map((question) => {
      const result = latestAnswers[keyFor(question)].result!;
      return {
        part_type: question.part_type,
        question_index: question.question_index,
        question,
        answer_text: result.transcript,
        audio_url: result.audio_url,
        audio_asset_id: result.audio_asset_id,
        transcript_text: result.transcript,
        voice_score: result.score,
        voice_feedback: result.feedback
      };
    });
    setSubmitting(true);
    setError("");
    try {
      const result = await evaluateMockTest(payload);
      onResult({ mockTestId: result.mock_test_id, answers: payload, report: result.report });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate the final mock test report.");
    } finally {
      setSubmitting(false);
    }
  }

  if (!questions.length && !loading) {
    return (
      <Stack spacing={2.25} sx={{ maxWidth: 950, alignItems: "flex-start" }}>
        <Typography variant="h2">Experience the Complete IELTS Speaking Test Flow</Typography>
        <Typography color="text.secondary" sx={{ maxWidth: 760, lineHeight: 1.65 }}>
          Record 6 Part 1 answers across two topics, 1 Part 2 response, and 4 Part 3 answers. Each recording is transcribed and scored before a final report is generated.
        </Typography>
        <TextField
          label="Practice goal"
          placeholder="Optional: technology, environment, work, difficult Part 3 questions..."
          value={practiceGoal}
          onChange={(event) => setPracticeGoal(event.target.value)}
          slotProps={{ htmlInput: { maxLength: 300 } }}
          fullWidth
        />
        <Alert severity="info" sx={{ width: "100%" }}>
          Leave the goal blank for a balanced mock test, or enter a topic to retrieve related questions. Questions come from a reviewed third-party IELTS Speaking practice question bank and are not presented as official exam questions.
        </Alert>
        {error ? <ErrorState message={error} /> : null}
        <Button variant="contained" onClick={handleStart}>Start Practice</Button>
      </Stack>
    );
  }

  if (loading) return <LoadingState label="Generating your full IELTS Speaking mock test..." />;
  if (!current) return <ErrorState message="The generated mock test did not contain any questions." />;

  const questionId = questionIdFor(current);
  const partProgress = (part: PartType) => {
    const partQuestions = sortedQuestions.filter((item) => item.part_type === part);
    const completed = partQuestions.filter((item) => answers[keyFor(item)]?.status === "completed").length;
    const currentPosition = part === current.part_type
      ? partQuestions.findIndex((item) => keyFor(item) === keyFor(current)) + 1
      : 0;
    return `${Math.max(completed, currentPosition)}/${partQuestions.length}`;
  };
  return (
    <Stack spacing={2.5}>
      <Box>
        <Stack direction="row" sx={{ justifyContent: "space-between", mb: 1 }}>
          <Typography sx={{ fontWeight: 700 }}>{labels[current.part_type]} · Question {current.question_index}</Typography>
          <Typography color="text.secondary">{currentIndex + 1} of {sortedQuestions.length}</Typography>
        </Stack>
        <LinearProgress variant="determinate" value={((currentIndex + 1) / sortedQuestions.length) * 100} />
      </Box>
      <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
        {(["part1", "part2", "part3"] as PartType[]).map((part) => (
          <Chip key={part} label={`${labels[part]} ${partProgress(part)}`} color={part === current.part_type ? "primary" : "default"} />
        ))}
      </Stack>
      {error ? <ErrorState message={error} /> : null}
      {sessionMetadata?.fallbackUsed ? (
        <Alert severity="warning">Semantic composition was unavailable, so a valid rule-based session was created.</Alert>
      ) : null}
      <SpokenQuestionCard
        question={current}
        voiceState={examinerVoice.voices[questionId]}
        onPlay={() => examinerVoice.play(questionId, current.question)}
        disabled={submitting || isRecording}
      />
      <VoiceAnswerRecorder
        ref={recorderRef}
        value={currentAnswer.recording}
        onChange={handleRecordingChange}
        maxDuration={maxDurations[current.part_type]}
        disabled={submitting}
        questionId={questionId}
        onRecordingStart={examinerVoice.stop}
        onPlaybackStart={examinerVoice.stop}
        onReRecord={handleReRecord}
        onRecordingStateChange={setIsRecording}
      />
      {currentAnswer.status === "completed" && currentAnswer.result ? (
        <Alert severity="success">
          Transcript saved · Band {currentAnswer.result.score.overall?.toFixed(1) ?? "N/A"}
          {currentAnswer.result.is_mock_transcript ? " · Mock ASR active" : ""}
        </Alert>
      ) : null}
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ justifyContent: "space-between" }}>
        <Button startIcon={<ArrowBackOutlinedIcon />} disabled={currentIndex === 0 || submitting || isRecording} onClick={handlePrevious}>Previous</Button>
        {currentIndex < sortedQuestions.length - 1 ? (
          <Button variant="contained" endIcon={<ArrowForwardOutlinedIcon />} disabled={submitting || isRecording || !currentAnswer.recording?.audioBlob} onClick={handleNext}>
            {submitting ? "Transcribing and scoring..." : "Next Question"}
          </Button>
        ) : (
          <Button variant="contained" disabled={submitting || isRecording || !currentAnswer.recording?.audioBlob} onClick={handleFinish}>
            {submitting ? "Generating Report..." : `Finish Test (${completed}/${sortedQuestions.length})`}
          </Button>
        )}
      </Stack>
    </Stack>
  );
}

export function flattenMockSession(session: MockSession): MockQuestion[] {
  const part1 = session.parts.part1.topics.flatMap((group) => group.questions).map((item, index) => ({
    part_type: "part1" as const,
    question_index: index + 1,
    question: item.text,
    cue_card: null,
    bank_question_id: item.id,
    topic: item.topic,
    source: item.source,
    difficulty: item.difficulty
  }));
  const cue = session.parts.part2.cueCard;
  const part2: MockQuestion = {
    part_type: "part2",
    question_index: 1,
    question: cue.prompt,
    cue_card: {
      topic: cue.topic,
      bullet_points: cue.bulletPoints,
      preparation_instruction: `You have ${cue.preparationTimeSeconds} seconds to prepare and up to ${cue.speakingTimeSeconds} seconds to speak.`,
      preparation_time_seconds: cue.preparationTimeSeconds,
      speaking_time_seconds: cue.speakingTimeSeconds
    },
    bank_question_id: cue.id,
    topic: cue.topic,
    source: cue.source,
    difficulty: cue.difficulty
  };
  const part3 = session.parts.part3.questions.map((item, index) => ({
    part_type: "part3" as const,
    question_index: index + 1,
    question: item.text,
    cue_card: null,
    bank_question_id: item.id,
    topic: item.topic,
    source: item.source,
    difficulty: item.difficulty
  }));
  return [...part1, part2, ...part3];
}
