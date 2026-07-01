import VolumeUpOutlinedIcon from "@mui/icons-material/VolumeUpOutlined";
import { Alert, Box, Button, Stack, Typography } from "@mui/material";
import type { ExaminerQuestion } from "../types/practice";
import type { ExaminerVoiceState } from "../hooks/useExaminerVoice";
import { Panel } from "./Layout";

export function SpokenQuestionCard({
  question,
  voiceState,
  onPlay,
  disabled
}: {
  question: ExaminerQuestion;
  voiceState?: ExaminerVoiceState;
  onPlay: () => void;
  disabled?: boolean;
}) {
  const label = voiceState?.isLoading
    ? "Generating examiner voice..."
    : voiceState?.isPlaying
      ? "Playing examiner voice..."
      : voiceState?.hasPlayed
        ? "Question Played"
        : "Play Examiner Question";
  return (
    <Panel>
      <Stack spacing={2}>
        <Box>
          <Typography color="secondary.main" sx={{ fontSize: 12, fontWeight: 800, textTransform: "uppercase" }}>Examiner Question</Typography>
          <Typography color="text.secondary" sx={{ mt: 1 }}>Listen carefully and answer naturally. The spoken question is hidden during practice.</Typography>
        </Box>
        <Button variant="contained" startIcon={<VolumeUpOutlinedIcon />} onClick={onPlay} disabled={disabled || voiceState?.isLoading || voiceState?.isPlaying || voiceState?.hasPlayed} sx={{ alignSelf: "flex-start" }}>
          {label}
        </Button>
        {voiceState?.errorMessage ? <Alert severity="error">{voiceState.errorMessage}</Alert> : null}
        {question.cue_card ? (
          <Box sx={{ p: 2.25, borderRadius: 2, bgcolor: "action.hover" }}>
            <Typography variant="h3">{question.cue_card.topic}</Typography>
            <Typography color="text.secondary" sx={{ mt: 1, mb: 1.25 }}>{question.cue_card.preparation_instruction}</Typography>
            <Box component="ul" sx={{ m: 0, pl: 2.5 }}>
              {question.cue_card.bullet_points.map((point) => <Typography component="li" key={point} sx={{ my: 1 }}>{point}</Typography>)}
            </Box>
          </Box>
        ) : null}
      </Stack>
    </Panel>
  );
}
