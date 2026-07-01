import { useState } from "react";
import { Box, List, ListItem, ListItemText, Stack, Tab, Tabs, Typography } from "@mui/material";
import type { MockAnswer, MockTestReport, PartFeedback, PartType } from "../types/practice";
import { QuestionCard } from "./QuestionCard";
import { PronunciationAssessmentView } from "./PronunciationAssessmentView";

const partTabs: Array<{ value: PartType; label: string }> = [
  { value: "part1", label: "Part 1" },
  { value: "part2", label: "Part 2" },
  { value: "part3", label: "Part 3" }
];

function score(value: number | null) {
  return value === null ? "N/A" : value.toFixed(1);
}

function ItemList({ items, empty = "No items returned." }: { items: string[]; empty?: string }) {
  if (!items.length) return <Typography color="text.secondary">{empty}</Typography>;
  return (
    <List dense disablePadding>
      {items.map((item, index) => (
        <ListItem key={`${item}-${index}`} disableGutters sx={{ alignItems: "flex-start", py: 0.4 }}>
          <ListItemText primary={item} slotProps={{ primary: { sx: { lineHeight: 1.55 } } }} />
        </ListItem>
      ))}
    </List>
  );
}

function SplitLists({
  leftTitle,
  leftItems,
  rightTitle,
  rightItems
}: {
  leftTitle: string;
  leftItems: string[];
  rightTitle: string;
  rightItems: string[];
}) {
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
        position: "relative",
        "&::after": {
          content: '\"\"',
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
      <Box sx={{ py: 3, pr: { md: 3 }, borderBottom: { xs: 1, md: 0 }, borderColor: "divider" }}>
        <Typography variant="h3" sx={{ mb: 1.25 }}>{leftTitle}</Typography>
        <ItemList items={leftItems} />
      </Box>
      <Box sx={{ py: 3, pl: { md: 3 } }}>
        <Typography variant="h3" sx={{ mb: 1.25 }}>{rightTitle}</Typography>
        <ItemList items={rightItems} />
      </Box>
    </Box>
  );
}

function BandBlock({ label, value }: { label: string; value: number | null }) {
  return (
    <Box
      sx={{
        width: { xs: "100%", sm: 260 },
        p: 2.5,
        borderRadius: 2,
        bgcolor: "primary.main",
        color: "primary.contrastText"
      }}
    >
      <Typography sx={{ fontSize: 13 }}>{label}</Typography>
      <Typography sx={{ fontSize: 40, fontWeight: 800, mt: 0.5 }}>{score(value)}</Typography>
    </Box>
  );
}

function PartReport({ partType, feedback, answers }: { partType: PartType; feedback: PartFeedback; answers: MockAnswer[] }) {
  const partAnswers = answers
    .filter((answer) => answer.part_type === partType)
    .sort((a, b) => a.question_index - b.question_index);

  return (
    <Box sx={{ borderTop: 1, borderBottom: 1, borderColor: "divider" }}>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={2.5}
        sx={{ py: 3, justifyContent: "space-between", alignItems: { xs: "stretch", sm: "flex-start" } }}
      >
        <Box sx={{ maxWidth: 780 }}>
          <Typography variant="h2">{partTabs.find((item) => item.value === partType)?.label} Feedback</Typography>
          <Typography color="text.secondary" sx={{ mt: 1.25, lineHeight: 1.65 }}>{feedback.summary}</Typography>
        </Box>
        <BandBlock label="Band estimate" value={feedback.band_estimate} />
      </Stack>

      <Box sx={{ borderTop: 1, borderColor: "divider" }}>
        <SplitLists
          leftTitle="Strengths"
          leftItems={feedback.strengths}
          rightTitle="Weaknesses"
          rightItems={feedback.weaknesses}
        />
      </Box>

      {partAnswers.map((answer) => {
        const analysis = feedback.question_analyses.find((item) => item.question_index === answer.question_index);
        return (
          <Box key={`${partType}-${answer.question_index}`} sx={{ borderTop: 1, borderColor: "divider" }}>
            <Stack direction="row" sx={{ py: 2.5, justifyContent: "space-between", alignItems: "center" }}>
              <Typography variant="h3">Question {answer.question_index}</Typography>
              <Typography color="primary.dark" sx={{ fontSize: 18, fontWeight: 800 }}>
                Band {score(analysis?.band_estimate ?? null)}
              </Typography>
            </Stack>
            <Box sx={{ borderTop: 1, borderColor: "divider" }}>
              <QuestionCard question={answer.question} plain />
            </Box>
            <Box sx={{ py: 3, borderTop: 1, borderColor: "divider" }}>
              <Typography color="secondary.main" sx={{ fontSize: 12, fontWeight: 800, textTransform: "uppercase" }}>
                Your Answer
              </Typography>
              <Typography sx={{ mt: 1.25, whiteSpace: "pre-wrap", lineHeight: 1.65 }}>{answer.answer_text}</Typography>
            </Box>
            {answer.audio_url ? (
              <Box sx={{ py: 3, borderTop: 1, borderColor: "divider" }}>
                <Typography variant="h3" sx={{ mb: 1.5 }}>Recording</Typography>
                <audio src={answer.audio_url} controls style={{ width: "100%" }} />
              </Box>
            ) : null}
            {answer.voice_score ? (
              <Box sx={{ py: 3, borderTop: 1, borderColor: "divider" }}>
                <Typography variant="h3" sx={{ mb: 1.5 }}>Criteria Scores</Typography>
                <Box sx={{ display: "grid", gridTemplateColumns: { xs: "repeat(2, 1fr)", md: "repeat(5, 1fr)" }, gap: 1.5 }}>
                  {[
                    ["Overall", answer.voice_score.overall],
                    ["Fluency", answer.voice_score.fluency_coherence],
                    ["Vocabulary", answer.voice_score.lexical_resource],
                    ["Grammar", answer.voice_score.grammatical_range_accuracy],
                    ["Pronunciation (estimated)", answer.voice_score.pronunciation]
                  ].map(([label, value]) => (
                    <Box key={String(label)} sx={{ p: 1.5, bgcolor: "action.hover", borderRadius: 1.5 }}>
                      <Typography color="text.secondary" sx={{ fontSize: 12 }}>{label}</Typography>
                      <Typography sx={{ mt: 0.5, fontSize: 22, fontWeight: 800 }}>{typeof value === "number" ? value.toFixed(1) : "N/A"}</Typography>
                    </Box>
                  ))}
                </Box>
                <PronunciationAssessmentView assessment={answer.voice_score.pronunciation_assessment} />
                {answer.voice_feedback?.summary ? <Typography sx={{ mt: 2, lineHeight: 1.65 }}>{answer.voice_feedback.summary}</Typography> : null}
                {answer.voice_feedback?.corrections.length ? (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="h3" sx={{ mb: 1 }}>Corrections</Typography>
                    <ItemList items={answer.voice_feedback.corrections.map((item) => `${item.original} → ${item.corrected}: ${item.reason}`)} />
                  </Box>
                ) : null}
                {answer.voice_feedback?.improved_answer ? (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="h3" sx={{ mb: 1 }}>Improved Answer</Typography>
                    <Typography sx={{ whiteSpace: "pre-wrap", lineHeight: 1.65 }}>{answer.voice_feedback.improved_answer}</Typography>
                  </Box>
                ) : null}
              </Box>
            ) : null}
            {analysis ? (
              <Box sx={{ borderTop: 1, borderColor: "divider" }}>
                <Box sx={{ py: 3 }}>
                  <Typography variant="h3" sx={{ mb: 1.25 }}>Analysis</Typography>
                  <Typography sx={{ lineHeight: 1.65 }}>{analysis.feedback}</Typography>
                </Box>
                <Box sx={{ borderTop: 1, borderColor: "divider" }}>
                  <SplitLists
                    leftTitle="Strengths"
                    leftItems={analysis.strengths}
                    rightTitle="Weaknesses"
                    rightItems={analysis.weaknesses}
                  />
                </Box>
                <Box sx={{ py: 3, borderTop: 1, borderColor: "divider" }}>
                  <Typography variant="h3" sx={{ mb: 1.25 }}>Improved Answer</Typography>
                  <Typography sx={{ whiteSpace: "pre-wrap", lineHeight: 1.65 }}>
                    {analysis.improved_answer || "No improved answer returned."}
                  </Typography>
                </Box>
              </Box>
            ) : null}
          </Box>
        );
      })}
    </Box>
  );
}

export function MockTestReportView({ report, answers }: { report: MockTestReport; answers: MockAnswer[] }) {
  const [tab, setTab] = useState<"overview" | PartType>("overview");
  const feedbackByPart: Record<PartType, PartFeedback> = {
    part1: report.part1_feedback,
    part2: report.part2_feedback,
    part3: report.part3_feedback
  };
  const azureScores = answers
    .map((answer) => answer.voice_score?.pronunciation_assessment?.pron_score)
    .filter((value): value is number => typeof value === "number");
  const averageAzureScore = azureScores.length
    ? azureScores.reduce((sum, value) => sum + value, 0) / azureScores.length
    : null;

  return (
    <Stack spacing={2.5}>
      <Tabs value={tab} onChange={(_, value) => setTab(value)} variant="scrollable" allowScrollButtonsMobile>
        <Tab value="overview" label="Overview" />
        {partTabs.map((item) => <Tab key={item.value} value={item.value} label={item.label} />)}
      </Tabs>

      {tab === "overview" ? (
        <Box sx={{ borderTop: 1, borderBottom: 1, borderColor: "divider" }}>
          <Box sx={{ py: 3 }}>
            <BandBlock label="Overall band estimate" value={report.overall_band_score} />
            {report.overall_feedback ? <Typography sx={{ mt: 2, maxWidth: 850, lineHeight: 1.65 }}>{report.overall_feedback}</Typography> : null}
            <Box sx={{ display: "grid", gridTemplateColumns: { xs: "repeat(2, 1fr)", md: "repeat(4, 1fr)" }, gap: 1.5, mt: 2.5 }}>
              {[
                ["Fluency & Coherence", report.criteria_scores.fluency_coherence],
                ["Lexical Resource", report.criteria_scores.lexical_resource],
                ["Grammar", report.criteria_scores.grammatical_range_accuracy],
                ["Pronunciation", report.criteria_scores.pronunciation]
              ].map(([label, value]) => (
                <Box key={String(label)} sx={{ p: 1.5, bgcolor: "action.hover", borderRadius: 1.5 }}>
                  <Typography color="text.secondary" sx={{ fontSize: 12 }}>{label}</Typography>
                  <Typography sx={{ mt: 0.5, fontSize: 22, fontWeight: 800 }}>{typeof value === "number" ? value.toFixed(1) : "N/A"}</Typography>
                </Box>
              ))}
            </Box>
            {averageAzureScore !== null ? (
              <Typography sx={{ mt: 2, fontWeight: 700 }}>
                Average Azure pronunciation score: {averageAzureScore.toFixed(1)}/100
              </Typography>
            ) : null}
          </Box>
          <Box sx={{ borderTop: 1, borderColor: "divider" }}>
            <SplitLists
              leftTitle="Key Strengths"
              leftItems={report.key_strengths}
              rightTitle="Key Weaknesses"
              rightItems={report.key_weaknesses}
            />
          </Box>
          <Box sx={{ py: 3, borderTop: 1, borderColor: "divider" }}>
            <Typography variant="h3" sx={{ mb: 1.25 }}>Next Practice Focus</Typography>
            <ItemList items={report.next_practice_focus.length ? report.next_practice_focus : report.action_plan} />
          </Box>
          {report.repeated_errors.length ? (
            <Box sx={{ py: 3, borderTop: 1, borderColor: "divider" }}>
              <Typography variant="h3" sx={{ mb: 1.25 }}>Repeated Errors</Typography>
              <ItemList items={report.repeated_errors.map((item) => `${item.error_type}: ${item.examples.join("; ")} — ${item.suggestion}`)} />
            </Box>
          ) : null}
          <Box sx={{ py: 3, borderTop: 1, borderColor: "divider" }}>
            <Typography variant="h3" sx={{ mb: 1.25 }}>Part Performance</Typography>
            <ItemList items={partTabs.map((item) => `${item.label}: ${report.part_performance[item.value] || feedbackByPart[item.value].summary}`)} />
          </Box>
        </Box>
      ) : (
        <PartReport partType={tab} feedback={feedbackByPart[tab]} answers={answers} />
      )}
    </Stack>
  );
}
