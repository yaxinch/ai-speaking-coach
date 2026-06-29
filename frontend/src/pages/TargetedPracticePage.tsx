import { Stack } from "@mui/material";
import { PartSelector } from "../components/PartSelector";
import { SectionHeader } from "../components/Layout";
import type { PartType } from "../types/practice";

export function TargetedPracticePage({ onSelect }: { onSelect: (partType: PartType) => void }) {
  return (
    <Stack spacing={2.75}>
      <SectionHeader
        title="Choose an IELTS Speaking Part"
        description="Work on one examiner-style question and receive focused AI feedback."
      />
      <PartSelector onSelect={onSelect} />
    </Stack>
  );
}
