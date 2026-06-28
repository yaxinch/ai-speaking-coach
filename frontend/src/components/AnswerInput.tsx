import { TextField } from "@mui/material";

export function AnswerInput({
  value,
  onChange,
  disabled
}: {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  return (
    <TextField
      label="Your answer"
      value={value}
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
      placeholder="Type your answer in English. Aim for a complete IELTS-style response with examples and details."
      multiline
      minRows={8}
      fullWidth
      variant="outlined"
      slotProps={{
        inputLabel: {
          shrink: true
        }
      }}
    />
  );
}
