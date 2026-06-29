import HistoryOutlinedIcon from "@mui/icons-material/HistoryOutlined";
import ReplayOutlinedIcon from "@mui/icons-material/ReplayOutlined";
import { Button, Stack } from "@mui/material";
import { MockTestReportView } from "../components/MockTestReportView";
import type { MockAnswer, MockTestReport } from "../types/practice";

export function FullMockResultPage({ report, answers, onNewTest, onHistory }: { report: MockTestReport; answers: MockAnswer[]; onNewTest: () => void; onHistory: () => void }) {
  return (
    <Stack spacing={2.75}>
      <MockTestReportView report={report} answers={answers} />
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
        <Button variant="contained" startIcon={<ReplayOutlinedIcon />} onClick={onNewTest}>New Full Mock Test</Button>
        <Button variant="outlined" startIcon={<HistoryOutlinedIcon />} onClick={onHistory}>View History</Button>
      </Stack>
    </Stack>
  );
}
