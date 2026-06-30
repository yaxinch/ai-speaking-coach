import { Box, Stack, Typography } from "@mui/material";
import type { PronunciationAssessment } from "../types/practice";

function metric(value: number | null) {
  return value === null ? "N/A" : value.toFixed(1);
}

export function PronunciationAssessmentView({ assessment }: { assessment?: PronunciationAssessment | null }) {
  if (!assessment) return null;

  return (
    <Box sx={{ mt: 3, pt: 3, borderTop: 1, borderColor: "divider" }}>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ justifyContent: "space-between" }}>
        <Typography variant="h3">Azure Pronunciation Assessment</Typography>
        <Typography color="primary.dark" sx={{ fontWeight: 800 }}>
          {assessment.available ? `Azure score: ${metric(assessment.pron_score)}/100` : "Azure score: N/A"}
        </Typography>
      </Stack>

      {assessment.available ? (
        <>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "repeat(2, 1fr)", md: "repeat(4, 1fr)" },
              mt: 2,
              borderTop: 1,
              borderBottom: 1,
              borderColor: "divider"
            }}
          >
            {[
              ["Estimated IELTS", assessment.estimated_ielts_band],
              ["Accuracy", assessment.accuracy_score],
              ["Azure Fluency", assessment.fluency_score],
              ["Prosody", assessment.prosody_score]
            ].map(([label, value], index) => (
              <Box
                key={String(label)}
                sx={{
                  py: 2,
                  px: 1.5,
                  borderRight: { xs: index % 2 === 0 ? 1 : 0, md: index < 3 ? 1 : 0 },
                  borderColor: "divider"
                }}
              >
                <Typography color="text.secondary" sx={{ fontSize: 12 }}>{label}</Typography>
                <Typography sx={{ mt: 0.5, fontSize: 22, fontWeight: 800 }}>{metric(value as number | null)}</Typography>
              </Box>
            ))}
          </Box>
          {assessment.weak_words.length ? (
            <Typography sx={{ mt: 2, lineHeight: 1.65 }}>
              <strong>Words to review:</strong>{" "}
              {assessment.weak_words.map((item) => `${item.word} (${item.accuracy_score.toFixed(0)})`).join(", ")}
            </Typography>
          ) : null}
        </>
      ) : null}
      <Typography color="text.secondary" sx={{ mt: 1.5, fontSize: 13, lineHeight: 1.55 }}>
        {assessment.message}
      </Typography>
    </Box>
  );
}
