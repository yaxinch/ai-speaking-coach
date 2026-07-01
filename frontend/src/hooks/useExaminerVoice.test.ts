import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { generateExaminerSpeech } from "../api/speaking";
import { useExaminerVoice } from "./useExaminerVoice";

vi.mock("../api/speaking", () => ({ generateExaminerSpeech: vi.fn() }));

class TestAudio {
  static instances: TestAudio[] = [];
  static rejectPlayback = false;
  currentTime = 0;
  onended: null | (() => void) = null;
  onerror: null | (() => void) = null;
  pause = vi.fn();
  play = vi.fn(() => TestAudio.rejectPlayback ? Promise.reject(new Error("blocked")) : Promise.resolve());

  constructor(public src: string) {
    TestAudio.instances.push(this);
  }
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

describe("useExaminerVoice", () => {
  beforeEach(() => {
    TestAudio.instances = [];
    TestAudio.rejectPlayback = false;
    vi.stubGlobal("Audio", TestAudio);
    vi.mocked(generateExaminerSpeech).mockReset();
  });

  it("ignores a stale TTS response after another question starts", async () => {
    const first = deferred<Blob>();
    const second = deferred<Blob>();
    vi.mocked(generateExaminerSpeech).mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    const { result } = renderHook(() => useExaminerVoice());

    let firstPlay!: Promise<void>;
    let secondPlay!: Promise<void>;
    act(() => {
      firstPlay = result.current.play("q1", "First question");
      secondPlay = result.current.play("q2", "Second question");
    });
    second.resolve(new Blob(["second"]));
    await act(async () => secondPlay);
    first.resolve(new Blob(["first"]));
    await act(async () => firstPlay);

    expect(TestAudio.instances).toHaveLength(1);
    expect(result.current.voices.q2.isPlaying).toBe(true);
    expect(result.current.voices.q1?.isPlaying).not.toBe(true);
    expect(URL.revokeObjectURL).toHaveBeenCalled();
  });

  it("allows retry after generation failure", async () => {
    vi.mocked(generateExaminerSpeech)
      .mockRejectedValueOnce(new Error("TTS unavailable"))
      .mockResolvedValueOnce(new Blob(["retry"]));
    const { result } = renderHook(() => useExaminerVoice());

    await act(async () => result.current.play("q1", "Question"));
    expect(result.current.voices.q1.errorMessage).toBe("TTS unavailable");
    await act(async () => result.current.play("q1", "Question"));

    await waitFor(() => expect(result.current.voices.q1.isPlaying).toBe(true));
    expect(generateExaminerSpeech).toHaveBeenCalledTimes(2);
  });

  it("surfaces browser playback failures", async () => {
    vi.mocked(generateExaminerSpeech).mockResolvedValue(new Blob(["voice"]));
    TestAudio.rejectPlayback = true;
    const { result } = renderHook(() => useExaminerVoice());

    await act(async () => result.current.play("q1", "Question"));

    expect(result.current.voices.q1.isPlaying).toBe(false);
    expect(result.current.voices.q1.hasPlayed).toBe(false);
    expect(result.current.voices.q1.errorMessage).toBe("Failed to play examiner voice.");
  });

  it("marks a question as consumed after playback starts and never plays it twice", async () => {
    vi.mocked(generateExaminerSpeech).mockResolvedValue(new Blob(["voice"]));
    const { result } = renderHook(() => useExaminerVoice());

    await act(async () => result.current.play("q1", "Question"));
    expect(result.current.voices.q1.hasPlayed).toBe(true);
    expect(result.current.voices.q1.isPlaying).toBe(true);

    act(() => TestAudio.instances[0].onended?.());
    expect(result.current.voices.q1.isPlaying).toBe(false);

    await act(async () => result.current.play("q1", "Question"));
    expect(generateExaminerSpeech).toHaveBeenCalledTimes(1);
    expect(TestAudio.instances).toHaveLength(1);
  });
});
