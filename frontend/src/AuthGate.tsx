import { useEffect, useState } from "react";
import { Box, CircularProgress } from "@mui/material";
import { App } from "./App";
import { getCurrentUser, login, logout, type AuthenticatedUser } from "./api/auth";
import { setUnauthorizedHandler } from "./api/client";
import { LoginPage } from "./pages/LoginPage";
import type { ColorMode } from "./theme";

type AuthState = { status: "loading" } | { status: "anonymous" } | { status: "authenticated"; user: AuthenticatedUser };

export function AuthGate({
  colorMode,
  onColorModeChange
}: {
  colorMode: ColorMode;
  onColorModeChange: (mode: ColorMode) => void;
}) {
  const [auth, setAuth] = useState<AuthState>({ status: "loading" });

  useEffect(() => {
    let active = true;
    setUnauthorizedHandler(() => setAuth({ status: "anonymous" }));
    getCurrentUser()
      .then((user) => {
        if (active) setAuth({ status: "authenticated", user });
      })
      .catch(() => {
        if (active) setAuth({ status: "anonymous" });
      });
    return () => {
      active = false;
      setUnauthorizedHandler(null);
    };
  }, []);

  async function handleLogin(username: string, password: string) {
    const user = await login(username, password);
    setAuth({ status: "authenticated", user });
  }

  async function handleLogout() {
    try {
      await logout();
      setAuth({ status: "anonymous" });
    } catch {
      // Keep the protected UI mounted when the server cannot confirm logout.
    }
  }

  if (auth.status === "loading") {
    return <Box aria-label="Checking sign-in status" sx={{ minHeight: "100vh", display: "grid", placeItems: "center" }}><CircularProgress /></Box>;
  }
  if (auth.status === "anonymous") return <LoginPage onLogin={handleLogin} />;
  return (
    <App
      colorMode={colorMode}
      onColorModeChange={onColorModeChange}
      username={auth.user.username}
      onLogout={handleLogout}
    />
  );
}
