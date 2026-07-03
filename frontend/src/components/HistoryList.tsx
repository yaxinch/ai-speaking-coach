import { Box, ButtonBase, Checkbox, Chip, Stack, Typography } from "@mui/material";
import type { HistoryEntry, PracticeMode } from "../types/practice";

const partLabel = {
  part1: "Part 1",
  part2: "Part 2",
  part3: "Part 3"
};

export function historyEntryKey(record: HistoryEntry): string {
  return `${record.mode}:${record.id}`;
}

export function parseHistoryTimestamp(value: string): Date {
  const hasTimeZone = /(?:Z|[+-]\d{2}:\d{2})$/i.test(value);
  return new Date(hasTimeZone ? value : `${value}Z`);
}

export function HistoryList({
  records,
  onOpen,
  selectionMode = false,
  selectedKeys = new Set<string>(),
  onToggle
}: {
  records: HistoryEntry[];
  onOpen: (mode: PracticeMode, practiceId: string) => void;
  selectionMode?: boolean;
  selectedKeys?: Set<string>;
  onToggle?: (record: HistoryEntry) => void;
}) {
  if (!records.length) {
    return <Typography color="text.secondary">No practice records yet.</Typography>;
  }

  return (
    <Stack spacing={1.25}>
      {records.map((record) => {
        const key = historyEntryKey(record);
        const selected = selectedKeys.has(key);
        return (
          <Stack key={key} direction="row" spacing={1} sx={{ alignItems: "center" }}>
            {selectionMode ? (
              <Checkbox
                checked={selected}
                onChange={() => onToggle?.(record)}
                slotProps={{ input: { "aria-label": `Select ${record.mode === "full_mock" ? "full mock test" : "targeted practice"}` } }}
              />
            ) : null}
            <ButtonBase
              onClick={() => selectionMode ? onToggle?.(record) : onOpen(record.mode, record.id)}
              sx={{
                flex: 1,
                display: "block",
                textAlign: "left",
                border: 1,
                borderColor: selected ? "primary.main" : "divider",
                borderRadius: 2,
                bgcolor: "background.paper",
                p: 2,
                "&:hover": { borderColor: "primary.main", bgcolor: "action.hover" }
              }}
            >
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "1fr", md: "190px 150px minmax(0, 1fr) 70px" },
                  gap: 1.75,
                  alignItems: "center"
                }}
              >
            <Typography color="text.secondary" sx={{ fontSize: 13 }}>
              {parseHistoryTimestamp(record.created_at).toLocaleString()}
            </Typography>
            <Chip
              label={record.mode === "full_mock" ? "Full Mock Test" : "Targeted Practice"}
              color={record.mode === "full_mock" ? "primary" : "default"}
              variant={record.mode === "full_mock" ? "filled" : "outlined"}
              sx={{ justifySelf: "start" }}
            />
            <Typography noWrap sx={{ fontWeight: 700 }}>
              {record.mode === "full_mock" ? "Part 1 · Part 2 · Part 3" : `${partLabel[record.part_type]} · ${record.question_text}`}
            </Typography>
            <Typography
              color="primary.dark"
              sx={{ fontSize: 18, fontWeight: 800, textAlign: { xs: "left", md: "right" } }}
            >
              {record.overall_band === null ? "N/A" : record.overall_band.toFixed(1)}
            </Typography>
              </Box>
            </ButtonBase>
          </Stack>
        );
      })}
    </Stack>
  );
}
