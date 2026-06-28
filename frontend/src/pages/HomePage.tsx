import { Stack, Typography } from "@mui/material";
import { PartSelector } from "../components/PartSelector";
import { Panel, SectionHeader } from "../components/Layout";
import type { PartType } from "../types/practice";

export function HomePage({ onStart }: { onStart: (partType: PartType) => void }) {
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
            Practice IELTS Speaking with examiner-style questions and structured AI feedback.
          </Typography>
          <Typography color="text.secondary">
            Select a speaking part, generate a prompt, submit a text answer, and review IELTS-style scoring with
            improvement suggestions.
          </Typography>
        </Stack>
      </Panel>

      <SectionHeader title="Choose Practice Mode" description="Start with the IELTS part you want to improve today." />
      <PartSelector onSelect={onStart} />
    </Stack>
  );
}
