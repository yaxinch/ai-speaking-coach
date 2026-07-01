import { useState } from "react";
import { Alert, Button, Stack, TextField } from "@mui/material";
import { startSectionPractice } from "../api/practices";
import { ErrorState } from "../components/ErrorState";
import { PartSelector } from "../components/PartSelector";
import { SectionHeader } from "../components/Layout";
import type { PartType, SectionPracticeStart } from "../types/practice";

export function TargetedPracticePage({
  onStart
}: {
  onStart: (partType: PartType, practiceGoal: string, selection: SectionPracticeStart) => void;
}) {
  const [selectedPart, setSelectedPart] = useState<PartType | undefined>();
  const [practiceGoal, setPracticeGoal] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleStart() {
    if (!selectedPart) {
      setError("Please choose an IELTS Speaking part.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const selection = await startSectionPractice(selectedPart, practiceGoal);
      onStart(selectedPart, practiceGoal.trim(), selection);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start section practice.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Stack spacing={2.75}>
      <SectionHeader
        title="Choose an IELTS Speaking Part"
        description="Work on one examiner-style question and receive focused AI feedback."
      />
      <PartSelector selected={selectedPart} onSelect={setSelectedPart} />
      <TextField
        label="Practice goal"
        placeholder="Optional: technology, environment, work, travel..."
        value={practiceGoal}
        onChange={(event) => setPracticeGoal(event.target.value)}
        slotProps={{ htmlInput: { maxLength: 300 } }}
        fullWidth
      />
      <Alert severity="info">
        Leave the goal blank for a random approved question from the selected Part, or enter a topic to retrieve a related question. Questions come from a reviewed third-party IELTS Speaking practice question bank.
      </Alert>
      {error ? <ErrorState message={error} /> : null}
      <Button variant="contained" onClick={handleStart} disabled={loading} sx={{ alignSelf: "flex-start" }}>
        {loading ? "Selecting Question..." : "Start Practice"}
      </Button>
    </Stack>
  );
}
