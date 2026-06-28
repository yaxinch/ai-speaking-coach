import { Box, Typography } from "@mui/material";
import type { ExaminerQuestion } from "../types/practice";
import { Panel } from "./Layout";

export function QuestionCard({ question, plain = false }: { question: ExaminerQuestion; plain?: boolean }) {
  const content = (
    <>
      <Typography color="secondary.main" sx={{ fontSize: 12, fontWeight: 800, textTransform: "uppercase" }}>
        Examiner Question
      </Typography>
      <Typography variant="h2" sx={{ mt: 1, lineHeight: 1.3 }}>
        {question.question}
      </Typography>
      {question.cue_card ? (
        <Box sx={{ mt: 2.25, p: 2.25, borderRadius: 2, bgcolor: "action.hover" }}>
          <Typography color="text.secondary" sx={{ mb: 1.25 }}>
            {question.cue_card.preparation_instruction}
          </Typography>
          <Box component="ul" sx={{ m: 0, pl: 2.5 }}>
            {question.cue_card.bullet_points.map((point) => (
              <Typography component="li" key={point} sx={{ my: 1 }}>
                {point}
              </Typography>
            ))}
          </Box>
        </Box>
      ) : null}
    </>
  );

  return plain ? <Box sx={{ py: 3 }}>{content}</Box> : <Panel>{content}</Panel>;
}
