import { Alert, Box, Typography } from "@mui/material";
import type { ExaminerQuestion, FeedbackResult } from "../types/practice";
import { FeedbackPanel } from "./FeedbackPanel";
import { QuestionCard } from "./QuestionCard";
import { ScoreSummary } from "./ScoreSummary";

export function TargetedPracticeReportView({
  question,
  userAnswer,
  feedback,
  audioUrl,
  isMockTranscript
}: {
  question: ExaminerQuestion;
  userAnswer: string;
  feedback: FeedbackResult;
  audioUrl?: string | null;
  isMockTranscript?: boolean;
}) {
  return (
    <Box sx={{ borderTop: 1, borderBottom: 1, borderColor: "divider" }}>
      <QuestionCard question={question} plain />
      <Box sx={{ py: 3, borderTop: 1, borderColor: "divider" }}>
        <Typography color="secondary.main" sx={{ fontSize: 12, fontWeight: 800, textTransform: "uppercase" }}>
          Your Answer
        </Typography>
        <Typography sx={{ mt: 1.25, whiteSpace: "pre-wrap", lineHeight: 1.65 }}>{userAnswer}</Typography>
      </Box>
      {audioUrl ? (
        <Box sx={{ py: 3, borderTop: 1, borderColor: "divider" }}>
          <Typography variant="h3" sx={{ mb: 1.5 }}>Your Recording</Typography>
          <audio src={audioUrl} controls style={{ width: "100%" }} />
        </Box>
      ) : null}
      {isMockTranscript ? (
        <Box sx={{ py: 3, borderTop: 1, borderColor: "divider" }}>
          <Alert severity="info">Mock ASR is active. The transcript is a fixed local-development response.</Alert>
        </Box>
      ) : null}
      <Box sx={{ borderTop: 1, borderColor: "divider" }}>
        <ScoreSummary feedback={feedback} plain />
      </Box>
      <FeedbackPanel feedback={feedback} plain />
    </Box>
  );
}
