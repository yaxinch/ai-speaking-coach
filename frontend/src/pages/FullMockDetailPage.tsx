import { useEffect, useState } from "react";
import ArrowBackOutlinedIcon from "@mui/icons-material/ArrowBackOutlined";
import { Button, Stack } from "@mui/material";
import { getMockTest } from "../api/mockTests";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { MockTestReportView } from "../components/MockTestReportView";
import type { MockTestDetail } from "../types/practice";

export function FullMockDetailPage({ mockTestId, onBack }: { mockTestId: string; onBack: () => void }) {
  const [record, setRecord] = useState<MockTestDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getMockTest(mockTestId).then(setRecord).catch((err) => setError(err instanceof Error ? err.message : "Failed to load mock test."));
  }, [mockTestId]);

  if (error) return <ErrorState message={error} />;
  if (!record) return <LoadingState label="Loading full mock test report..." />;
  return (
    <Stack spacing={2.5}>
      <Button variant="outlined" startIcon={<ArrowBackOutlinedIcon />} onClick={onBack} sx={{ alignSelf: "flex-start" }}>Back</Button>
      <MockTestReportView report={record.report} answers={record.answers} />
    </Stack>
  );
}
