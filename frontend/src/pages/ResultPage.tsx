import HistoryOutlinedIcon from "@mui/icons-material/HistoryOutlined";
import ReplayOutlinedIcon from "@mui/icons-material/ReplayOutlined";
import { Button, Stack, Typography } from "@mui/material";
import { FeedbackPanel } from "../components/FeedbackPanel";
import { Panel } from "../components/Layout";
import { QuestionCard } from "../components/QuestionCard";
import { ScoreSummary } from "../components/ScoreSummary";
import type { ExaminerQuestion, FeedbackResult } from "../types/practice";

export function ResultPage({
  question,
  userAnswer,
  feedback,
  onNewPractice,
  onHistory
}: {
  question: ExaminerQuestion;
  userAnswer: string;
  feedback: FeedbackResult;
  onNewPractice: () => void;
  onHistory: () => void;
}) {
  return (
    <Stack spacing={2.75} sx={{ maxWidth: 1120 }}>
      <QuestionCard question={question} />
      <Panel>
        <Typography color="secondary.main" sx={{ fontSize: 12, fontWeight: 800, textTransform: "uppercase" }}>
          Your Answer
        </Typography>
        <Typography sx={{ mt: 1.25, whiteSpace: "pre-wrap", lineHeight: 1.65 }}>{userAnswer}</Typography>
      </Panel>
      <ScoreSummary feedback={feedback} />
      <FeedbackPanel feedback={feedback} />
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
        <Button variant="contained" startIcon={<ReplayOutlinedIcon />} onClick={onNewPractice}>
          New Practice
        </Button>
        <Button variant="outlined" startIcon={<HistoryOutlinedIcon />} onClick={onHistory}>
          View History
        </Button>
      </Stack>
    </Stack>
  );
}
