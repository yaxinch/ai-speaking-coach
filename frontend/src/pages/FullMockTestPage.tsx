import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ArrowBackOutlinedIcon from "@mui/icons-material/ArrowBackOutlined";
import ArrowForwardOutlinedIcon from "@mui/icons-material/ArrowForwardOutlined";
import { Alert, Box, Button, Chip, LinearProgress, Stack, TextField, Typography } from "@mui/material";
import { startMockTest } from "../api/mockTests";
import { submitFullMockTest } from "../api/speaking";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { SpokenQuestionCard } from "../components/SpokenQuestionCard";
import { VoiceAnswerRecorder, type VoiceAnswerRecorderHandle } from "../components/VoiceAnswerRecorder";
import { useExaminerVoice } from "../hooks/useExaminerVoice";
import type { MockAnswer, MockQuestion, MockSession, MockTestReport, PartType, VoiceAnswerValue } from "../types/practice";

const order: Record<PartType, number> = { part1: 1, part2: 2, part3: 3 };
const labels: Record<PartType, string> = { part1: "Part 1", part2: "Part 2", part3: "Part 3" };
const maxDurations: Record<PartType, number> = { part1: 180, part2: 180, part3: 180 };

type AnswerStatus = "empty" | "recorded";
interface MockVoiceState {
  recording?: VoiceAnswerValue | null;
  status: AnswerStatus;
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
  const currentVoiceState = current ? examinerVoice.voices[questionIdFor(current)] : undefined;
  const completed = sortedQuestions.filter((question) => answers[keyFor(question)]?.status === "recorded").length;

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

  function handleNext() {
    if (isRecording) {
      setError("Please stop recording before moving to the next question.");
      return;
    }
    if (!currentAnswer.recording?.audioBlob) {
      return;
    }
    examinerVoice.stop();
    recorderRef.current?.stopPlayback();
    setError("");
    setCurrentIndex((value) => value + 1);
  }

  function handlePrevious() {
    examinerVoice.stop();
    recorderRef.current?.stopPlayback();
    setError("");
    setCurrentIndex((value) => Math.max(0, value - 1));
  }

  async function handleFinish() {
    if (isRecording) {
      setError("Please stop recording before finishing the test.");
      return;
    }
    const incomplete = sortedQuestions.filter((question) => !answers[keyFor(question)]?.recording?.audioBlob);
    if (incomplete.length) {
      setError(incomplete.map((question) => (
        question.part_type === "part2"
          ? "Part 2 Cue Card not recorded"
          : `${labels[question.part_type]} Question ${question.question_index} not recorded`
      )).join(" · "));
      return;
    }
    examinerVoice.stop();
    recorderRef.current?.stopPlayback();
    setSubmitting(true);
    setError("");
    try {
      const result = await submitFullMockTest({
        testId: sessionIdRef.current,
        questions: sortedQuestions.map((question) => {
          const recording = answers[keyFor(question)].recording!;
          return {
            questionId: questionIdFor(question),
            question,
            audioBlob: recording.audioBlob!,
            duration: recording.duration ?? 0,
            mimeType: recording.mimeType
          };
        })
      });
      onResult({ mockTestId: result.mock_test_id, answers: result.answers, report: result.report });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to transcribe and score the full mock test. Your recordings are still available; please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (!questions.length && !loading) {
    return (
      <Stack spacing={2.25} sx={{ maxWidth: 950, alignItems: "flex-start" }}>
        <Typography variant="h2">Experience the Complete IELTS Speaking Test Flow</Typography>
        <Typography color="text.secondary" sx={{ maxWidth: 760, lineHeight: 1.65 }}>
          Record 6 Part 1 answers across two topics, 1 Part 2 response, and 4 Part 3 answers. Your recordings are analyzed together after you finish the test.
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
    const completed = partQuestions.filter((item) => answers[keyFor(item)]?.status === "recorded").length;
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
        voiceState={currentVoiceState}
        onPlay={() => examinerVoice.play(questionId, current.question)}
        disabled={submitting || isRecording}
      />
      <VoiceAnswerRecorder
        ref={recorderRef}
        value={currentAnswer.recording}
        onChange={handleRecordingChange}
        maxDuration={maxDurations[current.part_type]}
        disabled={submitting || !currentVoiceState?.hasPlayed || currentVoiceState.isPlaying}
        questionId={questionId}
        onRecordingStart={examinerVoice.stop}
        onPlaybackStart={examinerVoice.stop}
        onRecordingStateChange={setIsRecording}
      />
      {currentAnswer.recording?.audioBlob ? <Alert severity="success">Recorded</Alert> : null}
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ justifyContent: "space-between" }}>
        <Button startIcon={<ArrowBackOutlinedIcon />} disabled={currentIndex === 0 || submitting || isRecording} onClick={handlePrevious}>Previous</Button>
        {currentIndex < sortedQuestions.length - 1 ? (
          <Button
            variant="contained"
            endIcon={<ArrowForwardOutlinedIcon />}
            disabled={submitting || isRecording || !currentAnswer.recording?.audioBlob}
            onClick={handleNext}
          >
            Next Question
          </Button>
        ) : (
          <Button variant="contained" disabled={submitting} onClick={handleFinish}>
            {submitting ? "Transcribing and scoring your full speaking test..." : `Finish Test (${completed}/${sortedQuestions.length})`}
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
