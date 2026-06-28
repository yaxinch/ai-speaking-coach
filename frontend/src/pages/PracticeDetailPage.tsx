import { useEffect, useState } from "react";
import ArrowBackOutlinedIcon from "@mui/icons-material/ArrowBackOutlined";
import { Box, Button, Stack, Typography } from "@mui/material";
import { getPractice } from "../api/practices";
import { ErrorState } from "../components/ErrorState";
import { FeedbackPanel } from "../components/FeedbackPanel";
import { LoadingState } from "../components/LoadingState";
import { QuestionCard } from "../components/QuestionCard";
import { ScoreSummary } from "../components/ScoreSummary";
import type { PracticeDetail } from "../types/practice";

export function PracticeDetailPage({ practiceId, onBack }: { practiceId: string; onBack: () => void }) {
  const [record, setRecord] = useState<PracticeDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getPractice(practiceId)
      .then(setRecord)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load practice detail."))
      .finally(() => setLoading(false));
  }, [practiceId]);

  if (loading) return <LoadingState label="Loading practice detail..." />;
  if (error) return <ErrorState message={error} />;
  if (!record) return <ErrorState message="Practice record not found." />;

  return (
    <Stack spacing={2.75} sx={{ maxWidth: 1120 }}>
      <Button variant="outlined" startIcon={<ArrowBackOutlinedIcon />} onClick={onBack} sx={{ alignSelf: "flex-start" }}>
        Back
      </Button>
      <Box sx={{ borderTop: 1, borderBottom: 1, borderColor: "divider" }}>
        <QuestionCard question={record.question} plain />
        <Box sx={{ py: 3, borderTop: 1, borderColor: "divider" }}>
          <Typography color="secondary.main" sx={{ fontSize: 12, fontWeight: 800, textTransform: "uppercase" }}>
            Your Answer
          </Typography>
          <Typography sx={{ mt: 1.25, whiteSpace: "pre-wrap", lineHeight: 1.65 }}>{record.user_answer}</Typography>
        </Box>
        <Box sx={{ borderTop: 1, borderColor: "divider" }}>
          <ScoreSummary feedback={record.feedback} plain />
        </Box>
        <FeedbackPanel feedback={record.feedback} plain />
      </Box>
    </Stack>
  );
}
