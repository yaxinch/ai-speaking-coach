import { useEffect, useMemo, useState } from "react";
import DarkModeOutlinedIcon from "@mui/icons-material/DarkModeOutlined";
import AssignmentTurnedInOutlinedIcon from "@mui/icons-material/AssignmentTurnedInOutlined";
import HistoryOutlinedIcon from "@mui/icons-material/HistoryOutlined";
import HomeOutlinedIcon from "@mui/icons-material/HomeOutlined";
import LightModeOutlinedIcon from "@mui/icons-material/LightModeOutlined";
import LogoutOutlinedIcon from "@mui/icons-material/LogoutOutlined";
import MenuBookOutlinedIcon from "@mui/icons-material/MenuBookOutlined";
import MessageOutlinedIcon from "@mui/icons-material/MessageOutlined";
import SettingsBrightnessOutlinedIcon from "@mui/icons-material/SettingsBrightnessOutlined";
import ViewSidebarOutlinedIcon from "@mui/icons-material/ViewSidebarOutlined";
import {
  Box,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  MenuItem,
  MenuList,
  Popover,
  Stack,
  Tooltip,
  Typography,
  type Theme
} from "@mui/material";
import { HomePage } from "./pages/HomePage";
import { PracticePage } from "./pages/PracticePage";
import { ResultPage } from "./pages/ResultPage";
import { HistoryPage } from "./pages/HistoryPage";
import { PracticeDetailPage } from "./pages/PracticeDetailPage";
import { TargetedPracticePage } from "./pages/TargetedPracticePage";
import { FullMockTestPage } from "./pages/FullMockTestPage";
import { FullMockResultPage } from "./pages/FullMockResultPage";
import { FullMockDetailPage } from "./pages/FullMockDetailPage";
import type { ColorMode } from "./theme";
import type { ExaminerQuestion, FeedbackResult, MockAnswer, MockTestReport, PartType, SectionPracticeStart } from "./types/practice";

type Route =
  | { name: "home" }
  | { name: "targeted" }
  | { name: "practice"; partType: PartType; practiceGoal: string; selection?: SectionPracticeStart }
  | {
      name: "result";
      practiceId: string;
      partType: PartType;
      question: ExaminerQuestion;
      userAnswer: string;
      feedback: FeedbackResult;
      audioUrl?: string;
      isMockTranscript?: boolean;
      practiceGoal: string;
    }
  | { name: "history" }
  | { name: "detail"; practiceId: string }
  | { name: "full-mock" }
  | { name: "full-mock-result"; mockTestId: string; answers: MockAnswer[]; report: MockTestReport }
  | { name: "full-mock-detail"; mockTestId: string };

const partLabels: Record<PartType, string> = {
  part1: "Part 1",
  part2: "Part 2",
  part3: "Part 3"
};

const colorModeOptions = [
  { value: "light", label: "Light", icon: LightModeOutlinedIcon },
  { value: "dark", label: "Dark", icon: DarkModeOutlinedIcon },
  { value: "system", label: "Follow system", icon: SettingsBrightnessOutlinedIcon }
] as const;

export function App({
  colorMode,
  onColorModeChange,
  username,
  onLogout
}: {
  colorMode: ColorMode;
  onColorModeChange: (mode: ColorMode) => void;
  username: string;
  onLogout: () => Promise<void>;
}) {
  const [route, setRoute] = useState<Route>({ name: "home" });
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [themeAnchor, setThemeAnchor] = useState<HTMLElement | null>(null);

  useEffect(() => {
    document.title = "AI Speaking Coach";
  }, []);

  const routeLabel = useMemo(() => {
    if (route.name === "practice") return `Practice ${partLabels[route.partType]}`;
    if (route.name === "targeted") return "Targeted Part Practice";
    if (route.name === "full-mock") return "Full Speaking Mock Test";
    if (route.name === "full-mock-result" || route.name === "full-mock-detail") return "Full Mock Test Report";
    if (route.name === "result") return "Feedback Result";
    if (route.name === "history") return "Practice History";
    if (route.name === "detail") return "Targeted Practice Report";
    return "Practice Dashboard";
  }, [route]);

  const navItems = [
    {
      label: "Dashboard",
      icon: HomeOutlinedIcon,
      active: route.name === "home",
      onClick: () => setRoute({ name: "home" } as Route)
    },
    {
      label: "Full Mock Test",
      icon: AssignmentTurnedInOutlinedIcon,
      active: route.name === "full-mock" || route.name === "full-mock-result",
      onClick: () => setRoute({ name: "full-mock" } as Route)
    },
    {
      label: "Targeted Practice",
      icon: MenuBookOutlinedIcon,
      active: route.name === "targeted" || route.name === "practice" || route.name === "result",
      onClick: () => setRoute({ name: "targeted" } as Route)
    },
    {
      label: "History",
      icon: HistoryOutlinedIcon,
      active: route.name === "history" || route.name === "detail" || route.name === "full-mock-detail",
      onClick: () => setRoute({ name: "history" } as Route)
    }
  ];

  const sidebarWidth = sidebarCollapsed ? 68 : 300;
  const selectedMode = colorModeOptions.find((option) => option.value === colorMode) ?? colorModeOptions[2];
  const SelectedModeIcon = selectedMode.icon;

  const sidebarButtonSx = (theme: Theme) => ({
    borderRadius: 1.5,
    minHeight: 44,
    width: "100%",
    minWidth: 0,
    px: sidebarCollapsed ? 0 : 1.25,
    justifyContent: sidebarCollapsed ? "center" : "flex-start",
    color: "#ffffff",
    whiteSpace: "nowrap",
    "&:hover": {
      bgcolor: "rgba(255, 255, 255, 0.16)",
      color: "#ffffff"
    },
    "&.Mui-selected, &.Mui-selected:hover": {
      bgcolor: theme.palette.mode === "dark" ? "rgba(255, 255, 255, 0.16)" : "#ffffff",
      color: theme.palette.mode === "dark" ? "#ffffff" : "#00AEEF"
    }
  } as const);

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: { xs: "block", md: "grid" },
        gridTemplateColumns: { md: `${sidebarWidth}px minmax(0, 1fr)` },
        transition: "grid-template-columns 180ms ease"
      }}
    >
      <Box
        component="aside"
        sx={{
          position: { xs: "relative", md: "sticky" },
          top: 0,
          height: { md: "100vh" },
          overflow: "hidden",
          bgcolor: (theme) => (theme.palette.mode === "dark" ? "#073B4C" : "#00AEEF"),
          color: "#ffffff",
          p: { xs: 2, md: sidebarCollapsed ? "18px 12px" : "18px 20px" },
          display: "flex",
          flexDirection: "column",
          gap: 2.5,
          alignItems: "stretch",
          transition: "padding 180ms ease"
        }}
      >
        <Box sx={{ position: "relative", width: "100%", minHeight: 44, display: "flex", alignItems: "center" }}>
          {!sidebarCollapsed ? (
            <Stack
              direction="row"
              spacing={1.25}
              sx={{ width: "100%", minWidth: 0, alignItems: "center", pr: 5.5 }}
            >
              <Box
                sx={{
                  width: 36,
                  height: 36,
                  flex: "0 0 auto",
                  display: "grid",
                  placeItems: "center",
                  borderRadius: 1.5,
                  bgcolor: "transparent",
                  color: "#ffffff"
                }}
              >
                <MessageOutlinedIcon sx={{ fontSize: 20 }} />
              </Box>
              <Typography noWrap sx={{ fontSize: 18, lineHeight: 1, fontWeight: 800 }}>
                AI Speaking Coach
              </Typography>
            </Stack>
          ) : null}

          <Tooltip
            title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            placement="right"
            disableFocusListener
          >
            <IconButton
              aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              onClick={() => setSidebarCollapsed((current) => !current)}
              size="small"
              sx={{
                display: { xs: "none", md: "inline-flex" },
                position: "absolute",
                right: sidebarCollapsed ? "50%" : -8,
                top: "50%",
                transform: sidebarCollapsed ? "translate(50%, -50%)" : "translateY(-50%)",
                width: 44,
                height: 44,
                borderRadius: 1.5,
                color: "#ffffff",
                zIndex: 2,
                "&:hover, &:focus-visible": { bgcolor: "rgba(255, 255, 255, 0.16)" }
              }}
            >
              <ViewSidebarOutlinedIcon
                sx={{
                  fontSize: 20,
                  transform: sidebarCollapsed ? "none" : "scaleX(-1)",
                  transition: "transform 180ms ease"
                }}
              />
            </IconButton>
          </Tooltip>
        </Box>

        <List component="nav" disablePadding sx={{ display: "flex", flexDirection: "column", gap: 0.75, width: "100%" }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <Tooltip key={item.label} title={sidebarCollapsed ? item.label : ""} placement="right">
                <ListItemButton selected={item.active} onClick={item.onClick} sx={sidebarButtonSx}>
                  <ListItemIcon
                    sx={{
                      color: (theme) => (item.active && theme.palette.mode !== "dark" ? "#00AEEF" : "#ffffff"),
                      minWidth: sidebarCollapsed ? 0 : 34,
                      justifyContent: "center"
                    }}
                  >
                    <Icon fontSize="small" />
                  </ListItemIcon>
                  {!sidebarCollapsed ? (
                    <ListItemText primary={item.label} slotProps={{ primary: { sx: { fontWeight: 400 } } }} />
                  ) : null}
                </ListItemButton>
              </Tooltip>
            );
          })}
        </List>

        <Box sx={{ mt: "auto", width: "100%" }}>
          <Tooltip title={sidebarCollapsed ? `Theme: ${selectedMode.label}` : ""} placement="right">
            <ListItemButton
              aria-label="Choose theme"
              onClick={(event) => setThemeAnchor(event.currentTarget)}
              sx={sidebarButtonSx}
            >
              <ListItemIcon
                sx={{ color: "#ffffff", minWidth: sidebarCollapsed ? 0 : 34, justifyContent: "center" }}
              >
                <SelectedModeIcon fontSize="small" />
              </ListItemIcon>
              {!sidebarCollapsed ? (
                <ListItemText primary={`Theme: ${selectedMode.label}`} slotProps={{ primary: { sx: { fontWeight: 400 } } }} />
              ) : null}
            </ListItemButton>
          </Tooltip>
          <Popover
            open={Boolean(themeAnchor)}
            anchorEl={themeAnchor}
            onClose={() => setThemeAnchor(null)}
            anchorOrigin={{ vertical: "top", horizontal: "left" }}
            transformOrigin={{ vertical: "bottom", horizontal: "left" }}
          >
            <MenuList dense sx={{ minWidth: 180, p: 0.75 }}>
              {colorModeOptions.map((option) => {
                const Icon = option.icon;
                return (
                  <MenuItem
                    key={option.value}
                    selected={colorMode === option.value}
                    onClick={() => {
                      onColorModeChange(option.value);
                      setThemeAnchor(null);
                    }}
                    sx={{ gap: 1.25, borderRadius: 1 }}
                  >
                    <Icon fontSize="small" color="primary" />
                    {option.label}
                  </MenuItem>
                );
              })}
            </MenuList>
          </Popover>
          <Tooltip title={sidebarCollapsed ? `Sign out ${username}` : ""} placement="right">
            <ListItemButton aria-label="Sign out" onClick={() => void onLogout()} sx={sidebarButtonSx}>
              <ListItemIcon sx={{ color: "#ffffff", minWidth: sidebarCollapsed ? 0 : 34, justifyContent: "center" }}>
                <LogoutOutlinedIcon fontSize="small" />
              </ListItemIcon>
              {!sidebarCollapsed ? <ListItemText primary={`Sign out (${username})`} /> : null}
            </ListItemButton>
          </Tooltip>
        </Box>
      </Box>

      <Box component="main" sx={{ minWidth: 0, p: { xs: 2.5, md: "32px 42px 48px" } }}>
        <Box sx={{ width: "100%", maxWidth: 1120, mx: "auto" }}>
          <Box component="header" sx={{ mb: 3.5 }}>
            <Typography color="secondary.main" sx={{ fontSize: 12, fontWeight: 800, textTransform: "uppercase" }}>
              IELTS Speaking
            </Typography>
            <Typography variant="h1" sx={{ mt: 0.5 }}>
              {routeLabel}
            </Typography>
          </Box>

          {route.name === "home" && (
            <HomePage
              onSelectMode={(mode) => setRoute(mode === "full_mock" ? { name: "full-mock" } : { name: "targeted" })}
            />
          )}
          {route.name === "targeted" && (
            <TargetedPracticePage
              onStart={(partType, practiceGoal, selection) =>
                setRoute({ name: "practice", partType, practiceGoal, selection })
              }
            />
          )}
          {route.name === "practice" && (
            <PracticePage
              partType={route.partType}
              practiceGoal={route.practiceGoal}
              initialSelection={route.selection}
              onBack={() => setRoute({ name: "targeted" })}
              onResult={(result) => setRoute({ name: "result", ...result })}
            />
          )}
          {route.name === "result" && (
            <ResultPage
              question={route.question}
              userAnswer={route.userAnswer}
              feedback={route.feedback}
              audioUrl={route.audioUrl}
              isMockTranscript={route.isMockTranscript}
              onNewPractice={() => setRoute({ name: "practice", partType: route.partType, practiceGoal: route.practiceGoal })}
              onHistory={() => setRoute({ name: "history" })}
            />
          )}
          {route.name === "full-mock" && (
            <FullMockTestPage onResult={(result) => setRoute({ name: "full-mock-result", ...result })} />
          )}
          {route.name === "full-mock-result" && (
            <FullMockResultPage
              report={route.report}
              answers={route.answers}
              onNewTest={() => setRoute({ name: "full-mock" })}
              onHistory={() => setRoute({ name: "history" })}
            />
          )}
          {route.name === "history" && (
            <HistoryPage
              onOpen={(mode, practiceId) =>
                setRoute(mode === "full_mock" ? { name: "full-mock-detail", mockTestId: practiceId } : { name: "detail", practiceId })
              }
            />
          )}
          {route.name === "detail" && (
            <PracticeDetailPage practiceId={route.practiceId} onBack={() => setRoute({ name: "history" })} />
          )}
          {route.name === "full-mock-detail" && (
            <FullMockDetailPage mockTestId={route.mockTestId} onBack={() => setRoute({ name: "history" })} />
          )}
        </Box>
      </Box>
    </Box>
  );
}
