import { Stack, Typography } from "@mui/material";
import { PracticeModeSelector } from "../components/PracticeModeSelector";
import { Panel, SectionHeader } from "../components/Layout";
import type { PracticeMode } from "../types/practice";

export function HomePage({ onSelectMode }: { onSelectMode: (mode: PracticeMode) => void }) {
  return (
    <Stack spacing={2.75} sx={{ maxWidth: 1120 }}>
      <Panel
        sx={{
          minHeight: 210,
          display: "flex",
          alignItems: "center",
          background: (theme) =>
            theme.palette.mode === "dark"
              ? "linear-gradient(120deg, rgba(0, 174, 239, 0.16), rgba(0, 135, 186, 0.08))"
              : "linear-gradient(120deg, rgba(0, 174, 239, 0.10), rgba(79, 200, 242, 0.06))"
        }}
      >
        <Stack spacing={1.25} sx={{ maxWidth: 820 }}>
          <Typography variant="h1" component="h2" sx={{ fontSize: { xs: 28, md: 34 } }}>
            Choose how you want to prepare for IELTS Speaking.
          </Typography>
          <Typography color="text.secondary">
            Take a complete three-part mock test or focus on one speaking part with examiner-style questions and
            structured AI feedback.
          </Typography>
        </Stack>
      </Panel>

      <SectionHeader title="Choose Practice Mode" description="Select a complete simulation or focused practice." />
      <PracticeModeSelector onSelect={onSelectMode} />
    </Stack>
  );
}
