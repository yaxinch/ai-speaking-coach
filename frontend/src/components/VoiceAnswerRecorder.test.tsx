import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { VoiceAnswerRecorder } from "./VoiceAnswerRecorder";

const mediaRecorder = vi.hoisted(() => ({
  options: null as null | Record<string, (...args: any[]) => void>,
  status: "idle",
  error: "",
  startRecording: vi.fn(),
  stopRecording: vi.fn(),
  clearBlobUrl: vi.fn()
}));

vi.mock("react-media-recorder", () => ({
  useReactMediaRecorder: (options: Record<string, (...args: any[]) => void>) => {
    mediaRecorder.options = options;
    return {
      status: mediaRecorder.status,
      error: mediaRecorder.error,
      startRecording: mediaRecorder.startRecording,
      stopRecording: mediaRecorder.stopRecording,
      clearBlobUrl: mediaRecorder.clearBlobUrl
    };
  }
}));

describe("VoiceAnswerRecorder", () => {
  beforeEach(() => {
    vi.useRealTimers();
    mediaRecorder.status = "idle";
    mediaRecorder.error = "";
    mediaRecorder.options = null;
    mediaRecorder.startRecording.mockReset();
    mediaRecorder.stopRecording.mockReset();
    mediaRecorder.clearBlobUrl.mockReset();
  });

  it("resets elapsed time, playback, and local errors when the question changes", async () => {
    const pause = vi.spyOn(HTMLMediaElement.prototype, "pause");
    const { rerender } = render(
      <VoiceAnswerRecorder
        questionId="question-1"
        value={{ audioBlob: new Blob(["voice"]), audioUrl: "blob:answer", duration: 37 }}
        onChange={vi.fn()}
      />
    );

    expect(screen.getByText("00:37")).toBeInTheDocument();
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("missing blob")));
    await act(async () => {
      await mediaRecorder.options?.onStop?.("blob:missing", new Blob());
    });
    expect(screen.getByText("Recording failed because no audio data was produced.")).toBeInTheDocument();

    rerender(<VoiceAnswerRecorder questionId="question-2" value={null} onChange={vi.fn()} />);

    expect(screen.getByText("00:00")).toBeInTheDocument();
    expect(screen.queryByText("Recording failed because no audio data was produced.")).not.toBeInTheDocument();
    expect(pause).toHaveBeenCalled();
    expect(mediaRecorder.clearBlobUrl).toHaveBeenCalled();
    vi.unstubAllGlobals();
  });

  it("stops automatically at the 180 second limit", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-06-30T00:00:00Z"));
    const onRecordingStateChange = vi.fn();
    const { rerender } = render(
      <VoiceAnswerRecorder questionId="question-1" value={null} onChange={vi.fn()} onRecordingStateChange={onRecordingStateChange} />
    );

    fireEvent.click(screen.getByRole("button", { name: "Start Recording" }));
    expect(mediaRecorder.startRecording).toHaveBeenCalledOnce();
    act(() => mediaRecorder.options?.onStart?.());
    mediaRecorder.status = "recording";
    rerender(
      <VoiceAnswerRecorder questionId="question-1" value={null} onChange={vi.fn()} onRecordingStateChange={onRecordingStateChange} />
    );

    act(() => vi.advanceTimersByTime(180_000));

    expect(mediaRecorder.stopRecording).toHaveBeenCalled();
    expect(screen.getByText("03:00")).toBeInTheDocument();
    expect(onRecordingStateChange).toHaveBeenCalledWith(true);
  });
});
