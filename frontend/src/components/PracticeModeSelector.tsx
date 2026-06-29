import AssignmentTurnedInOutlinedIcon from "@mui/icons-material/AssignmentTurnedInOutlined";
import TuneOutlinedIcon from "@mui/icons-material/TuneOutlined";
import { alpha, Box, Card, CardActionArea, Stack, Typography } from "@mui/material";
import type { PracticeMode } from "../types/practice";

const modes = [
  {
    mode: "full_mock" as const,
    title: "Full Speaking Mock Test",
    description: "Complete Part 1, Part 2, and Part 3 in one continuous 8-question session, then receive a full report.",
    icon: AssignmentTurnedInOutlinedIcon
  },
  {
    mode: "targeted" as const,
    title: "Targeted Part Practice",
    description: "Choose one IELTS Speaking part and focus on a single examiner-style question with detailed feedback.",
    icon: TuneOutlinedIcon
  }
];

export function PracticeModeSelector({ onSelect }: { onSelect: (mode: PracticeMode) => void }) {
  return (
    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)" }, gap: 2 }}>
      {modes.map((mode) => {
        const Icon = mode.icon;
        return (
          <Card key={mode.mode} variant="outlined">
            <CardActionArea onClick={() => onSelect(mode.mode)} sx={{ minHeight: 210, p: 3 }}>
              <Stack spacing={1.5} sx={{ alignItems: "flex-start" }}>
                <Box
                  sx={{
                    width: 48,
                    height: 48,
                    display: "grid",
                    placeItems: "center",
                    borderRadius: 2,
                    color: "primary.main",
                    bgcolor: (theme) => alpha(theme.palette.primary.main, 0.12)
                  }}
                >
                  <Icon />
                </Box>
                <Typography variant="h3">{mode.title}</Typography>
                <Typography color="text.secondary" sx={{ lineHeight: 1.6 }}>
                  {mode.description}
                </Typography>
              </Stack>
            </CardActionArea>
          </Card>
        );
      })}
    </Box>
  );
}
