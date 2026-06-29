import { useEffect, useState } from "react";
import ArrowBackOutlinedIcon from "@mui/icons-material/ArrowBackOutlined";
import RefreshOutlinedIcon from "@mui/icons-material/RefreshOutlined";
import SendOutlinedIcon from "@mui/icons-material/SendOutlined";
import { Button, Stack, Typography } from "@mui/material";
import { generateQuestion } from "../api/examiner";
import { evaluateAnswer } from "../api/feedback";
import { AnswerInput } from "../components/AnswerInput";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { QuestionCard } from "../components/QuestionCard";
import type { ExaminerQuestion, FeedbackResult, PartType } from "../types/practice";

const descriptions: Record<PartType, string> = {
  part1: "Short daily-life answers. Focus on natural responses with one or two details.",
  part2: "Cue card response. Build a structured story with clear sequencing and examples.",
  part3: "Abstract discussion. Expand your opinion with reasons, comparisons, and consequences."
};

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
  }) => void;
}) {
  const [question, setQuestion] = useState<ExaminerQuestion | null>(null);
  const [answer, setAnswer] = useState("");
  const [loadingQuestion, setLoadingQuestion] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function handleGenerate() {
    setLoadingQuestion(true);
    setError("");
    setAnswer("");
    try {
      setQuestion(await generateQuestion(partType));
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
    if (!answer.trim()) {
      setError("Answer cannot be empty.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const result = await evaluateAnswer(partType, question, answer);
      onResult({
        practiceId: result.practice_id,
        partType,
        question,
        userAnswer: answer,
        feedback: result.feedback
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
      {question && !loadingQuestion ? <QuestionCard question={question} /> : null}

      <AnswerInput value={answer} onChange={setAnswer} disabled={submitting || loadingQuestion} />
      <Button
        variant="contained"
        startIcon={<SendOutlinedIcon />}
        onClick={handleSubmit}
        disabled={submitting || loadingQuestion}
        sx={{ alignSelf: "flex-start" }}
      >
        {submitting ? "Evaluating..." : "Submit Answer"}
      </Button>
    </Stack>
  );
}
