import type { ReactNode } from "react";
import { Card, CardContent, Stack, Typography, type SxProps, type Theme } from "@mui/material";

export function SectionHeader({ title, description }: { title?: string; description?: string }) {
  return (
    <Stack spacing={0.75}>
      {title ? <Typography variant="h2">{title}</Typography> : null}
      {description ? <Typography color="text.secondary">{description}</Typography> : null}
    </Stack>
  );
}

export function Panel({ children, sx }: { children: ReactNode; sx?: SxProps<Theme> }) {
  return (
    <Card variant="outlined" sx={{ borderColor: "divider", ...sx }}>
      <CardContent>{children}</CardContent>
    </Card>
  );
}
