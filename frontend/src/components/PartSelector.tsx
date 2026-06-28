import AssignmentOutlinedIcon from "@mui/icons-material/AssignmentOutlined";
import ChatBubbleOutlineOutlinedIcon from "@mui/icons-material/ChatBubbleOutlineOutlined";
import TimerOutlinedIcon from "@mui/icons-material/TimerOutlined";
import { alpha, Box, Card, CardActionArea, Stack, Typography } from "@mui/material";
import type { PartType } from "../types/practice";

const parts: Array<{
  partType: PartType;
  title: string;
  description: string;
  icon: typeof ChatBubbleOutlineOutlinedIcon;
}> = [
  {
    partType: "part1",
    title: "Part 1",
    description: "Daily-life short answers for fluency and basic expression.",
    icon: ChatBubbleOutlineOutlinedIcon
  },
  {
    partType: "part2",
    title: "Part 2",
    description: "Cue card practice for one to two minutes of structured speaking.",
    icon: TimerOutlinedIcon
  },
  {
    partType: "part3",
    title: "Part 3",
    description: "Abstract discussion questions for logic and opinion development.",
    icon: AssignmentOutlinedIcon
  }
];

export function PartSelector({
  selected,
  onSelect
}: {
  selected?: PartType;
  onSelect: (partType: PartType) => void;
}) {
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", md: "repeat(3, 1fr)" },
        gap: 2
      }}
    >
      {parts.map((part) => {
        const Icon = part.icon;
        return (
          <Card
            key={part.partType}
            variant="outlined"
            sx={{
              borderColor: selected === part.partType ? "primary.main" : "divider",
              boxShadow: selected === part.partType ? "0 12px 24px rgba(0, 174, 239, 0.14)" : undefined
            }}
          >
            <CardActionArea onClick={() => onSelect(part.partType)} sx={{ minHeight: 170, p: 2.5 }}>
              <Stack spacing={1.25} sx={{ alignItems: "flex-start" }}>
                <Box
                  sx={{
                    width: 42,
                    height: 42,
                    display: "grid",
                    placeItems: "center",
                    borderRadius: 2,
                    color: "primary.main",
                    bgcolor: (theme) => alpha(theme.palette.primary.main, 0.12)
                  }}
                >
                  <Icon fontSize="small" />
                </Box>
                <Typography variant="h3">{part.title}</Typography>
                <Typography color="text.secondary" sx={{ lineHeight: 1.5 }}>
                  {part.description}
                </Typography>
              </Stack>
            </CardActionArea>
          </Card>
        );
      })}
    </Box>
  );
}
