import { Alert, CircularProgress } from "@mui/material";

export function LoadingState({ label = "Loading..." }: { label?: string }) {
  return (
    <Alert icon={<CircularProgress color="inherit" size={18} />} severity="info" sx={{ alignItems: "center" }}>
      {label}
    </Alert>
  );
}
