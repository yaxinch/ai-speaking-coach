import { useEffect, useState } from "react";
import { Stack } from "@mui/material";
import { listPractices } from "../api/practices";
import { ErrorState } from "../components/ErrorState";
import { HistoryList } from "../components/HistoryList";
import { SectionHeader } from "../components/Layout";
import { LoadingState } from "../components/LoadingState";
import type { PracticeSummary } from "../types/practice";

export function HistoryPage({ onOpen }: { onOpen: (practiceId: string) => void }) {
  const [records, setRecords] = useState<PracticeSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    listPractices()
      .then(setRecords)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load history."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <Stack spacing={2.75} sx={{ maxWidth: 1120 }}>
      <SectionHeader description="Review previous answers and AI feedback." />
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {!loading && !error ? <HistoryList records={records} onOpen={onOpen} /> : null}
    </Stack>
  );
}
