import HistoryOutlinedIcon from "@mui/icons-material/HistoryOutlined";
import ReplayOutlinedIcon from "@mui/icons-material/ReplayOutlined";
import { Button, Stack } from "@mui/material";
import { TargetedPracticeReportView } from "../components/TargetedPracticeReportView";
import type { ExaminerQuestion, FeedbackResult } from "../types/practice";

export function ResultPage({
  question,
  userAnswer,
  feedback,
  onNewPractice,
  onHistory,
  audioUrl,
  isMockTranscript
}: {
  question: ExaminerQuestion;
  userAnswer: string;
  feedback: FeedbackResult;
  onNewPractice: () => void;
  onHistory: () => void;
  audioUrl?: string;
  isMockTranscript?: boolean;
}) {
  return (
    <Stack spacing={2.75} sx={{ maxWidth: 1120 }}>
      <TargetedPracticeReportView
        question={question}
        userAnswer={userAnswer}
        feedback={feedback}
        audioUrl={audioUrl}
        isMockTranscript={isMockTranscript}
      />
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
