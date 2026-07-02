import { useState, type FormEvent } from "react";
import MessageOutlinedIcon from "@mui/icons-material/MessageOutlined";
import { Alert, Box, Button, Card, CardContent, Stack, TextField, Typography } from "@mui/material";

export function LoginPage({
  onLogin
}: {
  onLogin: (username: string, password: string) => Promise<void>;
}) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(false);
    try {
      await onLogin(username, password);
    } catch {
      setError(true);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Box sx={{ minHeight: "100vh", display: "grid", placeItems: "center", p: 2.5 }}>
      <Card variant="outlined" sx={{ width: "100%", maxWidth: 440 }}>
        <CardContent sx={{ p: { xs: 3, sm: 4 } }}>
          <Stack component="form" spacing={2.5} onSubmit={handleSubmit}>
            <Stack spacing={1} sx={{ alignItems: "center", textAlign: "center" }}>
              <Box sx={{ width: 48, height: 48, display: "grid", placeItems: "center", borderRadius: 2, bgcolor: "primary.main", color: "white" }}>
                <MessageOutlinedIcon />
              </Box>
              <Typography variant="h1">AI Speaking Coach</Typography>
              <Typography color="text.secondary">Sign in to access the private demo.</Typography>
            </Stack>
            {error ? <Alert severity="error">Incorrect username or password.</Alert> : null}
            <TextField
              label="Username"
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
              autoFocus
            />
            <TextField
              label="Password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
            <Button type="submit" variant="contained" size="large" disabled={submitting}>
              {submitting ? "Signing in…" : "Sign in"}
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
