import { Box, Typography } from "@mui/material";
import type { FeedbackResult } from "../types/practice";
import { Panel } from "./Layout";

function scoreText(score: number | null) {
  return score === null || Number.isNaN(score) ? "N/A" : score.toFixed(1);
}

export function ScoreSummary({ feedback, plain = false }: { feedback: FeedbackResult; plain?: boolean }) {
  const scores = [
    ["Overall", feedback.overall_band_score],
    ["Fluency", feedback.fluency_score],
    ["Vocabulary", feedback.vocabulary_score],
    ["Grammar", feedback.grammar_score]
  ] as const;

  const content = (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", lg: "repeat(4, 1fr)" },
        gap: 1.75
      }}
    >
      {scores.map(([label, score], index) => (
        <Box
          key={label}
          sx={{
            p: 2.25,
            border: 1,
            borderColor: index === 0 ? "primary.main" : "divider",
            borderRadius: 2,
            bgcolor: index === 0 ? "primary.main" : "action.hover",
            color: index === 0 ? "primary.contrastText" : "text.primary"
          }}
        >
          <Typography sx={{ fontSize: 13, color: index === 0 ? "inherit" : "text.secondary" }}>{label}</Typography>
          <Typography component="strong" sx={{ display: "block", fontSize: 32, fontWeight: 800, mt: 1 }}>
            {scoreText(score)}
          </Typography>
        </Box>
      ))}
    </Box>
  );

  return plain ? <Box sx={{ py: 3 }}>{content}</Box> : <Panel>{content}</Panel>;
}
