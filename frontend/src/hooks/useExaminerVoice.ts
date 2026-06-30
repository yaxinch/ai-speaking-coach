import { useCallback, useEffect, useRef, useState } from "react";
import { generateExaminerSpeech } from "../api/speaking";

export interface ExaminerVoiceState {
  questionId: string;
  audioUrl?: string;
  isLoading: boolean;
  isPlaying: boolean;
  errorMessage?: string;
}

export function useExaminerVoice(onBeforePlay?: () => void) {
  const [voices, setVoices] = useState<Record<string, ExaminerVoiceState>>({});
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const urlsRef = useRef<Record<string, string>>({});
  const inFlightRef = useRef<Set<string>>(new Set());
  const requestVersionRef = useRef(0);

  const stop = useCallback(() => {
    requestVersionRef.current += 1;
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current = null;
    }
    setVoices((current) => Object.fromEntries(Object.entries(current).map(([key, value]) => [key, { ...value, isPlaying: false }])));
  }, []);

  const play = useCallback(async (questionId: string, text: string) => {
    if (inFlightRef.current.has(questionId)) return;
    stop();
    const requestVersion = requestVersionRef.current;
    onBeforePlay?.();
    let audioUrl = urlsRef.current[questionId];
    if (!audioUrl) {
      inFlightRef.current.add(questionId);
      setVoices((current) => ({ ...current, [questionId]: { questionId, isLoading: true, isPlaying: false } }));
      try {
        const blob = await generateExaminerSpeech({ question_id: questionId, text, voice: "Kore", accent: "british", speed: 0.95 });
        audioUrl = URL.createObjectURL(blob);
        if (requestVersion !== requestVersionRef.current) {
          URL.revokeObjectURL(audioUrl);
          return;
        }
        urlsRef.current[questionId] = audioUrl;
      } catch (error) {
        if (requestVersion !== requestVersionRef.current) return;
        setVoices((current) => ({ ...current, [questionId]: { questionId, isLoading: false, isPlaying: false, errorMessage: error instanceof Error ? error.message : "Failed to generate examiner voice. Please try again." } }));
        return;
      } finally {
        inFlightRef.current.delete(questionId);
      }
    }
    if (requestVersion !== requestVersionRef.current) return;
    const audio = new Audio(audioUrl);
    audioRef.current = audio;
    audio.onended = () => setVoices((current) => ({ ...current, [questionId]: { ...(current[questionId] ?? { questionId }), audioUrl, isLoading: false, isPlaying: false } }));
    audio.onerror = () => setVoices((current) => ({ ...current, [questionId]: { ...(current[questionId] ?? { questionId }), audioUrl, isLoading: false, isPlaying: false, errorMessage: "This audio format is not supported by your browser." } }));
    setVoices((current) => ({ ...current, [questionId]: { questionId, audioUrl, isLoading: false, isPlaying: true } }));
    try {
      await audio.play();
    } catch {
      setVoices((current) => ({ ...current, [questionId]: { questionId, audioUrl, isLoading: false, isPlaying: false, errorMessage: "Failed to play examiner voice." } }));
    }
  }, [onBeforePlay, stop]);

  const clear = useCallback((questionId: string) => {
    stop();
    const url = urlsRef.current[questionId];
    if (url) URL.revokeObjectURL(url);
    delete urlsRef.current[questionId];
    setVoices((current) => {
      const next = { ...current };
      delete next[questionId];
      return next;
    });
  }, [stop]);

  useEffect(() => () => {
    requestVersionRef.current += 1;
    if (audioRef.current) audioRef.current.pause();
    Object.values(urlsRef.current).forEach(URL.revokeObjectURL);
  }, []);

  return { voices, play, stop, clear };
}
