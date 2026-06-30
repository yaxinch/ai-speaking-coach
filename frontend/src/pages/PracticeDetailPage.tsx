import { useEffect, useState } from "react";
import ArrowBackOutlinedIcon from "@mui/icons-material/ArrowBackOutlined";
import { Button, Stack } from "@mui/material";
import { getPractice } from "../api/practices";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { TargetedPracticeReportView } from "../components/TargetedPracticeReportView";
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
      <TargetedPracticeReportView
        question={record.question}
        userAnswer={record.user_answer}
        feedback={record.feedback}
        audioUrl={record.audio_url}
      />
    </Stack>
  );
}
