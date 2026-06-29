import { useEffect, useState } from "react";
import { Stack } from "@mui/material";
import { listPractices } from "../api/practices";
import { listMockTests } from "../api/mockTests";
import { ErrorState } from "../components/ErrorState";
import { HistoryList } from "../components/HistoryList";
import { SectionHeader } from "../components/Layout";
import { LoadingState } from "../components/LoadingState";
import type { HistoryEntry, PracticeMode } from "../types/practice";

export function HistoryPage({ onOpen }: { onOpen: (mode: PracticeMode, practiceId: string) => void }) {
  const [records, setRecords] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([listPractices(), listMockTests()])
      .then(([targeted, mockTests]) => {
        const combined: HistoryEntry[] = [
          ...targeted.map((record) => ({ ...record, mode: "targeted" as const })),
          ...mockTests
        ];
        combined.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        setRecords(combined);
      })
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
