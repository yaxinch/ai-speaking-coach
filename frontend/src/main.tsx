import React, { useMemo, useState } from "react";
import ReactDOM from "react-dom/client";
import { CssBaseline, ThemeProvider, useMediaQuery } from "@mui/material";
import { App } from "./App";
import { createAppTheme, type ColorMode } from "./theme";
import "./styles/index.css";

function Root() {
  const [colorMode, setColorMode] = useState<ColorMode>(() => {
    const saved = window.localStorage.getItem("color-mode");
    return saved === "light" || saved === "dark" || saved === "system" ? saved : "system";
  });
  const systemDark = useMediaQuery("(prefers-color-scheme: dark)");
  const resolvedMode = colorMode === "system" ? (systemDark ? "dark" : "light") : colorMode;
  const theme = useMemo(() => createAppTheme(resolvedMode), [resolvedMode]);

  function handleColorModeChange(nextMode: ColorMode) {
    setColorMode(nextMode);
    window.localStorage.setItem("color-mode", nextMode);
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <App colorMode={colorMode} onColorModeChange={handleColorModeChange} />
    </ThemeProvider>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
);
