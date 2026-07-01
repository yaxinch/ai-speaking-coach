import { useEffect, useState } from "react";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlineOutlined";
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, Typography } from "@mui/material";
import { deletePractice, listPractices } from "../api/practices";
import { deleteMockTest, listMockTests } from "../api/mockTests";
import { ErrorState } from "../components/ErrorState";
import { HistoryList, historyEntryKey } from "../components/HistoryList";
import { SectionHeader } from "../components/Layout";
import { LoadingState } from "../components/LoadingState";
import type { HistoryEntry, PracticeMode } from "../types/practice";

export function HistoryPage({ onOpen }: { onOpen: (mode: PracticeMode, practiceId: string) => void }) {
  const [records, setRecords] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const selectedRecords = records.filter((record) => selectedKeys.has(historyEntryKey(record)));

  function toggleRecord(record: HistoryEntry) {
    const key = historyEntryKey(record);
    setSelectedKeys((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function exitSelectionMode() {
    setSelectionMode(false);
    setSelectedKeys(new Set());
    setConfirmDelete(false);
  }

  async function handleDeleteSelected() {
    if (!selectedRecords.length) return;
    setDeleting(true);
    setError("");
    const results = await Promise.allSettled(
      selectedRecords.map((record) => record.mode === "full_mock" ? deleteMockTest(record.id) : deletePractice(record.id))
    );
    const deletedKeys = new Set(
      selectedRecords
        .filter((_, index) => results[index].status === "fulfilled")
        .map(historyEntryKey)
    );
    const failedKeys = new Set(
      selectedRecords
        .filter((_, index) => results[index].status === "rejected")
        .map(historyEntryKey)
    );
    setRecords((current) => current.filter((record) => !deletedKeys.has(historyEntryKey(record))));
    setDeleting(false);
    setConfirmDelete(false);
    if (failedKeys.size) {
      setSelectedKeys(failedKeys);
      setError(`${failedKeys.size} history record${failedKeys.size === 1 ? "" : "s"} could not be deleted. Please try again.`);
    } else {
      exitSelectionMode();
    }
  }

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
      {!loading && records.length ? (
        selectionMode ? (
          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={1.25}
            sx={{
              width: "100%",
              justifyContent: "flex-end",
              alignItems: { xs: "flex-end", sm: "center" }
            }}
          >
            <Typography sx={{ fontWeight: 700 }}>{selectedRecords.length} selected</Typography>
            <Button
              variant="outlined"
              onClick={() => setSelectedKeys(
                selectedRecords.length === records.length
                  ? new Set()
                  : new Set(records.map(historyEntryKey))
              )}
            >
              {selectedRecords.length === records.length ? "Clear Selection" : "Select All"}
            </Button>
            <Button
              variant="contained"
              color="error"
              startIcon={<DeleteOutlineIcon />}
              disabled={!selectedRecords.length}
              onClick={() => setConfirmDelete(true)}
            >
              Delete Selected
            </Button>
            <Button onClick={exitSelectionMode}>Cancel</Button>
          </Stack>
        ) : (
          <Button
            variant="outlined"
            color="error"
            startIcon={<DeleteOutlineIcon />}
            onClick={() => setSelectionMode(true)}
            sx={{ alignSelf: "flex-end" }}
          >
            Select History to Delete
          </Button>
        )
      ) : null}
      {!loading ? (
        <HistoryList
          records={records}
          onOpen={onOpen}
          selectionMode={selectionMode}
          selectedKeys={selectedKeys}
          onToggle={toggleRecord}
        />
      ) : null}
      <Dialog open={confirmDelete} onClose={() => !deleting && setConfirmDelete(false)}>
        <DialogTitle>Delete {selectedRecords.length} History Record{selectedRecords.length === 1 ? "" : "s"}?</DialogTitle>
        <DialogContent>This permanently removes the selected reports, transcripts, scores, feedback, and associated recordings.</DialogContent>
        <DialogActions>
          <Button disabled={deleting} onClick={() => setConfirmDelete(false)}>Cancel</Button>
          <Button disabled={deleting} color="error" onClick={handleDeleteSelected}>{deleting ? "Deleting..." : "Delete"}</Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
