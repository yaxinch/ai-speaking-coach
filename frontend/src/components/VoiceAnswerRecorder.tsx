import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlineOutlined";
import FiberManualRecordIcon from "@mui/icons-material/FiberManualRecord";
import StopCircleOutlinedIcon from "@mui/icons-material/StopCircleOutlined";
import { Alert, Box, Button, Stack, Typography } from "@mui/material";
import { useReactMediaRecorder } from "react-media-recorder";
import type { VoiceAnswerValue } from "../types/practice";
import { Panel } from "./Layout";

export interface VoiceAnswerRecorderHandle {
  stopPlayback: () => void;
}

export interface VoiceAnswerRecorderProps {
  value?: VoiceAnswerValue | null;
  onChange: (value: VoiceAnswerValue | null) => void;
  maxDuration?: number;
  disabled?: boolean;
  questionId?: string;
  onRecordingStart?: () => void;
  onReRecord?: () => void;
  onPlaybackStart?: () => void;
  onRecordingStateChange?: (recording: boolean) => void;
}

const errorMessages: Record<string, string> = {
  permission_denied: "Microphone permission was denied. Allow microphone access and try again.",
  no_specified_media_found: "No microphone was found on this device.",
  media_in_use: "The microphone is currently in use by another application.",
  invalid_media_constraints: "This browser cannot use the requested microphone settings.",
  media_aborted: "Microphone access was interrupted.",
  recorder_error: "Recording failed. Please try again.",
  no_constraints: "This browser does not support audio recording."
};

function clock(seconds: number) {
  const safe = Math.max(0, Math.floor(seconds));
  return `${String(Math.floor(safe / 60)).padStart(2, "0")}:${String(safe % 60).padStart(2, "0")}`;
}

export const VoiceAnswerRecorder = forwardRef<VoiceAnswerRecorderHandle, VoiceAnswerRecorderProps>(
  function VoiceAnswerRecorder(
    { value, onChange, maxDuration = 300, disabled, questionId, onRecordingStart, onReRecord, onPlaybackStart, onRecordingStateChange },
    ref
  ) {
    const [elapsed, setElapsed] = useState(0);
    const [localError, setLocalError] = useState("");
    const timerRef = useRef<number | null>(null);
    const startedAtRef = useRef(0);
    const audioRef = useRef<HTMLAudioElement | null>(null);
    const statusRef = useRef("");
    const stopRecordingRef = useRef<() => void>(() => undefined);
    const clearBlobUrlRef = useRef<() => void>(() => undefined);

    const recorder = useReactMediaRecorder({
      audio: true,
      video: false,
      stopStreamsOnStop: true,
      onStart: () => {
        startedAtRef.current = Date.now();
        setElapsed(0);
        setLocalError("");
        onRecordingStart?.();
        onRecordingStateChange?.(true);
      },
      onStop: async (blobUrl, fallbackBlob) => {
        if (timerRef.current !== null) window.clearInterval(timerRef.current);
        timerRef.current = null;
        onRecordingStateChange?.(false);
        const duration = Math.min(maxDuration, Math.max(1, (Date.now() - startedAtRef.current) / 1000));
        try {
          const response = await fetch(blobUrl);
          const blob = await response.blob();
          const usableBlob = blob.size ? blob : fallbackBlob;
          const ownedUrl = URL.createObjectURL(usableBlob);
          onChange({ audioBlob: usableBlob, audioUrl: ownedUrl, duration, mimeType: usableBlob.type || "audio/webm", recordedAt: new Date().toISOString() });
          setElapsed(duration);
        } catch {
          if (fallbackBlob.size) {
            const ownedUrl = URL.createObjectURL(fallbackBlob);
            onChange({ audioBlob: fallbackBlob, audioUrl: ownedUrl, duration, mimeType: fallbackBlob.type || "audio/webm", recordedAt: new Date().toISOString() });
          } else {
            setLocalError("Recording failed because no audio data was produced.");
          }
        } finally {
          recorder.clearBlobUrl();
        }
      }
    });

    const recording = recorder.status === "recording";
    statusRef.current = recorder.status;
    stopRecordingRef.current = recorder.stopRecording;
    clearBlobUrlRef.current = recorder.clearBlobUrl;

    useEffect(() => {
      if (!recording) return;
      timerRef.current = window.setInterval(() => {
        const next = (Date.now() - startedAtRef.current) / 1000;
        setElapsed(next);
        if (next >= maxDuration) recorder.stopRecording();
      }, 250);
      return () => {
        if (timerRef.current !== null) window.clearInterval(timerRef.current);
        timerRef.current = null;
      };
    }, [recording, maxDuration, recorder.stopRecording]);

    useEffect(() => {
      audioRef.current?.pause();
      if (audioRef.current) audioRef.current.currentTime = 0;
      recorder.clearBlobUrl();
      setElapsed(value?.duration ?? 0);
      setLocalError("");
    }, [questionId]);

    useEffect(() => () => {
      if (statusRef.current === "recording") stopRecordingRef.current();
      clearBlobUrlRef.current();
      if (timerRef.current !== null) window.clearInterval(timerRef.current);
      audioRef.current?.pause();
    }, []);

    useImperativeHandle(ref, () => ({
      stopPlayback: () => {
        audioRef.current?.pause();
        if (audioRef.current) audioRef.current.currentTime = 0;
      }
    }), []);

    const browserUnsupported = typeof MediaRecorder === "undefined" || !navigator.mediaDevices?.getUserMedia;
    const recorderError = errorMessages[recorder.error] || localError;

    function handleReRecord() {
      audioRef.current?.pause();
      recorder.clearBlobUrl();
      setElapsed(0);
      setLocalError("");
      onChange(null);
      onReRecord?.();
    }

    return (
      <Panel>
        <Stack spacing={2}>
          <Box>
            <Typography variant="h3">Your spoken answer</Typography>
            <Typography color={recording ? "error.main" : "text.secondary"} sx={{ mt: 0.75 }}>
              {recording ? "Recording..." : value?.audioBlob ? "Recorded" : "Ready to record"}
            </Typography>
          </Box>
          <Typography sx={{ fontSize: 34, fontWeight: 800, fontVariantNumeric: "tabular-nums" }}>
            {clock(recording ? elapsed : value?.duration ?? elapsed)}
          </Typography>
          {browserUnsupported ? <Alert severity="error">This browser does not support audio recording.</Alert> : null}
          {recorderError ? <Alert severity="error">{recorderError}</Alert> : null}
          {value?.audioUrl && !recording ? (
            <audio ref={audioRef} src={value.audioUrl} controls onPlay={onPlaybackStart} style={{ width: "100%" }} />
          ) : null}
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
            {!recording && !value?.audioBlob ? (
              <Button variant="contained" startIcon={<FiberManualRecordIcon />} onClick={recorder.startRecording} disabled={disabled || browserUnsupported}>
                Start Recording
              </Button>
            ) : null}
            {recording ? (
              <Button variant="contained" color="error" startIcon={<StopCircleOutlinedIcon />} onClick={recorder.stopRecording} disabled={disabled}>
                Stop Recording
              </Button>
            ) : null}
            {!recording && value?.audioBlob ? (
              <Button variant="outlined" startIcon={<DeleteOutlineIcon />} onClick={handleReRecord} disabled={disabled}>
                Re-record
              </Button>
            ) : null}
          </Stack>
          <Typography color="text.secondary" sx={{ fontSize: 13 }}>Maximum recording time: {clock(maxDuration)}</Typography>
        </Stack>
      </Panel>
    );
  }
);
