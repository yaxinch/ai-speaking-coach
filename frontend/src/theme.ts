import { alpha, createTheme } from "@mui/material/styles";
import type { PaletteMode } from "@mui/material";

export type ColorMode = PaletteMode | "system";

export function createAppTheme(mode: PaletteMode) {
  const isDark = mode === "dark";

  return createTheme({
    palette: {
      mode,
      primary: {
        main: "#00AEEF",
        light: "#4FC8F2",
        dark: "#0087BA",
        contrastText: "#ffffff"
      },
      secondary: {
        main: isDark ? "#72D8F7" : "#0087BA"
      },
      background: {
        default: isDark ? "#101820" : "#f4f8fa",
        paper: isDark ? "#18232d" : "#ffffff"
      },
      text: {
        primary: isDark ? "#f3f7f9" : "#152536",
        secondary: isDark ? "#aebdc7" : "#607080"
      },
      divider: isDark ? "#31414d" : "#d7e3e9",
      error: {
        main: "#c94139"
      }
    },
    typography: {
      fontFamily: [
        "Inter",
        "ui-sans-serif",
        "system-ui",
        "-apple-system",
        "BlinkMacSystemFont",
        "\"Segoe UI\"",
        "sans-serif"
      ].join(","),
      h1: {
        fontSize: "1.875rem",
        lineHeight: 1.15,
        fontWeight: 800,
        letterSpacing: 0
      },
      h2: {
        fontSize: "1.5rem",
        lineHeight: 1.25,
        fontWeight: 800,
        letterSpacing: 0
      },
      h3: {
        fontSize: "1.125rem",
        lineHeight: 1.3,
        fontWeight: 800,
        letterSpacing: 0
      },
      button: {
        fontWeight: 700,
        textTransform: "none",
        letterSpacing: 0
      }
    },
    shape: {
      borderRadius: 8
    },
    components: {
      MuiButton: {
        defaultProps: {
          disableElevation: true
        },
        styleOverrides: {
          root: {
            minHeight: 44,
            borderRadius: 8
          }
        }
      },
      MuiCard: {
        styleOverrides: {
          root: {
            borderRadius: 8,
            boxShadow: isDark ? "none" : "0 10px 24px rgba(15, 54, 72, 0.05)"
          }
        }
      },
      MuiCardContent: {
        styleOverrides: {
          root: {
            padding: 24,
            "&:last-child": {
              paddingBottom: 24
            }
          }
        }
      },
      MuiListItemButton: {
        styleOverrides: {
          root: {
            "&.Mui-selected": {
              backgroundColor: isDark ? alpha("#ffffff", 0.16) : alpha("#00AEEF", 0.2)
            }
          }
        }
      }
    }
  });
}
