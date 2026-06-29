import { useMemo, useState } from "react";
import ArrowBackOutlinedIcon from "@mui/icons-material/ArrowBackOutlined";
import ArrowForwardOutlinedIcon from "@mui/icons-material/ArrowForwardOutlined";
import { Alert, Box, Button, Chip, LinearProgress, Stack, Typography } from "@mui/material";
import { evaluateMockTest, generateMockTest } from "../api/mockTests";
import { AnswerInput } from "../components/AnswerInput";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { QuestionCard } from "../components/QuestionCard";
import type { MockAnswer, MockQuestion, MockTestReport, PartType } from "../types/practice";

const order: Record<PartType, number> = { part1: 1, part2: 2, part3: 3 };
const labels: Record<PartType, string> = { part1: "Part 1", part2: "Part 2", part3: "Part 3" };

export function FullMockTestPage({
  onResult
}: {
  onResult: (result: { mockTestId: string; answers: MockAnswer[]; report: MockTestReport }) => void;
}) {
  const [questions, setQuestions] = useState<MockQuestion[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const sortedQuestions = useMemo(
    () => [...questions].sort((a, b) => order[a.part_type] - order[b.part_type] || a.question_index - b.question_index),
    [questions]
  );
  const current = sortedQuestions[currentIndex];
  const keyFor = (question: MockQuestion) => `${question.part_type}-${question.question_index}`;
  const completed = sortedQuestions.filter((question) => answers[keyFor(question)]?.trim()).length;

  async function handleStart() {
    setLoading(true);
    setError("");
    try {
      const result = await generateMockTest();
      setQuestions(result.questions);
      setAnswers({});
      setCurrentIndex(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate a full mock test.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit() {
    if (completed !== sortedQuestions.length) {
      setError(`Complete all ${sortedQuestions.length} answers before submitting.`);
      return;
    }
    const payload: MockAnswer[] = sortedQuestions.map((question) => ({
      part_type: question.part_type,
      question_index: question.question_index,
      question,
      answer_text: answers[keyFor(question)].trim(),
      audio_url: null,
      transcript_text: null
    }));
    setSubmitting(true);
    setError("");
    try {
      const result = await evaluateMockTest(payload);
      onResult({ mockTestId: result.mock_test_id, answers: payload, report: result.report });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to evaluate the mock test.");
    } finally {
      setSubmitting(false);
    }
  }

  if (!questions.length && !loading) {
    return (
      <Stack spacing={2.25} sx={{ maxWidth: 950, alignItems: "flex-start" }}>
        <Typography variant="h2">Experience the Complete IELTS Speaking Test Flow</Typography>
        <Typography color="text.secondary" sx={{ maxWidth: 760, lineHeight: 1.65 }}>
          Complete 4 Part 1 questions, 1 Part 2 cue card, and 3 Part 3 questions. Your answers are evaluated together at the end.
        </Typography>
        <Alert severity="info" sx={{ width: "100%" }}>
          This text-based session contains 8 questions. Set aside enough time to answer each one fully.
        </Alert>
        {error ? <ErrorState message={error} /> : null}
        <Button variant="contained" onClick={handleStart}>Start Full Mock Test</Button>
      </Stack>
    );
  }

  if (loading) return <LoadingState label="Generating your full IELTS Speaking mock test..." />;
  if (!current) return <ErrorState message="The generated mock test did not contain any questions." />;

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
          <Chip key={part} label={`${labels[part]} ${sortedQuestions.filter((item) => item.part_type === part && answers[keyFor(item)]?.trim()).length}/${sortedQuestions.filter((item) => item.part_type === part).length}`} color={part === current.part_type ? "primary" : "default"} />
        ))}
      </Stack>
      {error ? <ErrorState message={error} /> : null}
      <QuestionCard question={current} />
      <AnswerInput
        value={answers[keyFor(current)] ?? ""}
        onChange={(value) => setAnswers((existing) => ({ ...existing, [keyFor(current)]: value }))}
        disabled={submitting}
      />
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ justifyContent: "space-between" }}>
        <Button startIcon={<ArrowBackOutlinedIcon />} disabled={currentIndex === 0 || submitting} onClick={() => setCurrentIndex((value) => value - 1)}>Previous</Button>
        {currentIndex < sortedQuestions.length - 1 ? (
          <Button variant="contained" endIcon={<ArrowForwardOutlinedIcon />} disabled={submitting} onClick={() => setCurrentIndex((value) => value + 1)}>Next Question</Button>
        ) : (
          <Button variant="contained" disabled={submitting || completed !== sortedQuestions.length} onClick={handleSubmit}>
            {submitting ? "Generating Report..." : `Submit Full Test (${completed}/${sortedQuestions.length})`}
          </Button>
        )}
      </Stack>
    </Stack>
  );
}
