import { Box, List, ListItem, ListItemText, Typography } from "@mui/material";
import type { FeedbackResult } from "../types/practice";
import { Panel } from "./Layout";

function ListBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <Box>
      <Typography variant="h3" sx={{ mb: 1.5 }}>
        {title}
      </Typography>
      {items.length ? (
        <List dense disablePadding>
          {items.map((item) => (
            <ListItem key={item} disableGutters sx={{ alignItems: "flex-start", py: 0.5 }}>
              <ListItemText primary={item} slotProps={{ primary: { sx: { lineHeight: 1.5 } } }} />
            </ListItem>
          ))}
        </List>
      ) : (
        <Typography color="text.secondary">No items returned.</Typography>
      )}
    </Box>
  );
}

export function FeedbackPanel({ feedback, plain = false }: { feedback: FeedbackResult; plain?: boolean }) {
  const extra = (
    <>
      {feedback.summary ? (
        <Box sx={{ py: 3, borderTop: 1, borderColor: "divider" }}>
          <Typography variant="h3" sx={{ mb: 1.5 }}>Feedback Summary</Typography>
          <Typography sx={{ lineHeight: 1.65 }}>{feedback.summary}</Typography>
        </Box>
      ) : null}
      {feedback.corrections?.length ? (
        <Box sx={{ py: 3, borderTop: 1, borderColor: "divider" }}>
          <Typography variant="h3" sx={{ mb: 1.5 }}>Corrections</Typography>
          {feedback.corrections.map((item, index) => (
            <Box key={`${item.original}-${index}`} sx={{ py: 1 }}>
              <Typography><s>{item.original}</s> → <strong>{item.corrected}</strong></Typography>
              <Typography color="text.secondary" sx={{ mt: 0.5 }}>{item.reason}</Typography>
            </Box>
          ))}
        </Box>
      ) : null}
    </>
  );
  if (plain) {
    return (
      <Box>
        {extra}
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
            position: "relative",
            borderTop: 1,
            borderColor: "divider",
            "&::after": {
              content: '""',
              display: { xs: "none", md: "block" },
              position: "absolute",
              top: 24,
              bottom: 24,
              left: "50%",
              width: "1px",
              bgcolor: "divider"
            }
          }}
        >
          <Box
            sx={{
              py: 3,
              pr: { md: 3 },
              borderBottom: { xs: 1, md: 0 },
              borderColor: "divider"
            }}
          >
            <ListBlock title="Strengths" items={feedback.strengths} />
          </Box>
          <Box sx={{ py: 3, pl: { md: 3 } }}>
            <ListBlock title="Weaknesses" items={feedback.weaknesses} />
          </Box>
        </Box>
        <Box sx={{ py: 3, borderTop: 1, borderColor: "divider" }}>
          <Typography variant="h3" sx={{ mb: 1.5 }}>
            Improved Answer
          </Typography>
          <Typography sx={{ whiteSpace: "pre-wrap", lineHeight: 1.65 }}>
            {feedback.improved_answer || "No improved answer returned."}
          </Typography>
        </Box>
        <Box sx={{ py: 3, borderTop: 1, borderColor: "divider" }}>
          <ListBlock title="Action Suggestions" items={feedback.action_suggestions} />
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)" }, gap: 2 }}>
      {(feedback.summary || feedback.corrections?.length) ? <Panel sx={{ gridColumn: { xs: "auto", md: "1 / -1" } }}>{extra}</Panel> : null}
      <Panel>
        <ListBlock title="Strengths" items={feedback.strengths} />
      </Panel>
      <Panel>
        <ListBlock title="Weaknesses" items={feedback.weaknesses} />
      </Panel>
      <Panel sx={{ gridColumn: { xs: "auto", md: "1 / -1" } }}>
        <Typography variant="h3" sx={{ mb: 1.5 }}>
          Improved Answer
        </Typography>
        <Typography sx={{ whiteSpace: "pre-wrap", lineHeight: 1.65 }}>
          {feedback.improved_answer || "No improved answer returned."}
        </Typography>
      </Panel>
      <Panel sx={{ gridColumn: { xs: "auto", md: "1 / -1" } }}>
        <ListBlock title="Action Suggestions" items={feedback.action_suggestions} />
      </Panel>
    </Box>
  );
}
