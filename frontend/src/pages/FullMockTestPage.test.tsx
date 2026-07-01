import { forwardRef, useImperativeHandle } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { MockQuestion, MockSession, MockTestReport, VoiceAnswerResult } from "../types/practice";
import { FullMockTestPage } from "./FullMockTestPage";

const api = vi.hoisted(() => ({
  startMockTest: vi.fn(),
  evaluateMockTest: vi.fn(),
  submitVoiceAnswer: vi.fn(),
  deletePendingAudio: vi.fn()
}));

vi.mock("../api/mockTests", () => ({
  startMockTest: api.startMockTest,
  evaluateMockTest: api.evaluateMockTest
}));

vi.mock("../api/speaking", () => ({
  submitVoiceAnswer: api.submitVoiceAnswer,
  deletePendingAudio: api.deletePendingAudio
}));

vi.mock("../hooks/useExaminerVoice", () => ({
  useExaminerVoice: () => ({ voices: {}, play: vi.fn(), stop: vi.fn(), clear: vi.fn() })
}));

vi.mock("../components/SpokenQuestionCard", () => ({
  SpokenQuestionCard: ({ question }: { question: MockQuestion }) => <div>Prompt: {question.question}</div>
}));

vi.mock("../components/VoiceAnswerRecorder", () => ({
  VoiceAnswerRecorder: forwardRef(function Recorder(
    { value, onChange }: { value?: { audioBlob?: Blob }; onChange: (value: unknown) => void },
    ref
  ) {
    useImperativeHandle(ref, () => ({ stopPlayback: vi.fn() }));
    return (
      <button
        type="button"
        onClick={() => onChange({ audioBlob: new Blob(["voice"], { type: "audio/webm" }), audioUrl: "blob:answer", duration: 10, mimeType: "audio/webm" })}
      >
        {value?.audioBlob ? "Recorded answer" : "Record answer"}
      </button>
    );
  })
}));

const questions: MockQuestion[] = [
  ...Array.from({ length: 6 }, (_, index) => ({ part_type: "part1" as const, question_index: index + 1, question: `Part 1 question ${index + 1}`, cue_card: null })),
  { part_type: "part2", question_index: 1, question: "Part 2 question 1", cue_card: null },
  ...Array.from({ length: 4 }, (_, index) => ({ part_type: "part3" as const, question_index: index + 1, question: `Part 3 question ${index + 1}`, cue_card: null }))
];

const session: MockSession = {
  sessionId: "session-id",
  practiceGoal: null,
  mode: "default",
  parts: {
    part1: {
      topics: ["Topic A", "Topic B"].map((topic, topicIndex) => ({
        topic,
        questions: Array.from({ length: 3 }, (_, index) => ({
          id: `p1-${topicIndex}-${index}`,
          text: `Part 1 question ${topicIndex * 3 + index + 1}`,
          topic,
          source: "Practice source",
          difficulty: "easy" as const
        }))
      }))
    },
    part2: {
      cueCard: {
        id: "p2-1", topic: "Technology", prompt: "Describe useful technology", bulletPoints: ["what it is"],
        preparationTimeSeconds: 60, speakingTimeSeconds: 120, source: "Practice source", difficulty: "medium"
      }
    },
    part3: {
      questions: Array.from({ length: 4 }, (_, index) => ({
        id: `p3-${index}`, text: `Part 3 question ${index + 1}`, topic: "Technology",
        source: "Practice source", difficulty: "hard" as const
      }))
    }
  },
  metadata: { retrievalUsed: false, candidateCount: 0, composerUsed: false, fallbackUsed: false, fallbackReason: null, createdAt: "2026-07-01T00:00:00Z" }
};

const report: MockTestReport = {
  overall_band_score: 7,
  key_strengths: [],
  key_weaknesses: [],
  action_plan: [],
  part1_feedback: { band_estimate: 7, summary: "", strengths: [], weaknesses: [], question_analyses: [] },
  part2_feedback: { band_estimate: 7, summary: "", strengths: [], weaknesses: [], question_analyses: [] },
  part3_feedback: { band_estimate: 7, summary: "", strengths: [], weaknesses: [], question_analyses: [] }
};

function voiceResult(sequence: number): VoiceAnswerResult {
  return {
    practice_id: null,
    audio_asset_id: `audio-${sequence}`,
    audio_url: `/api/speaking/audio/audio-${sequence}`,
    transcript: `Transcript ${sequence}`,
    asr_provider: "mock",
    is_mock_transcript: true,
    score: {
      overall: 7,
      fluency_coherence: 7,
      lexical_resource: 7,
      grammatical_range_accuracy: 7,
      pronunciation: null
    },
    feedback: {
      summary: "Good",
      strengths: [],
      weaknesses: [],
      corrections: [],
      improved_answer: "Improved",
      next_practice_suggestion: "Continue",
      pronunciation_note: "N/A"
    }
  };
}

describe("FullMockTestPage", () => {
  beforeEach(() => {
    api.startMockTest.mockReset().mockResolvedValue(session);
    api.submitVoiceAnswer.mockReset();
    questions.forEach((_, index) => api.submitVoiceAnswer.mockResolvedValueOnce(voiceResult(index + 1)));
    api.evaluateMockTest.mockReset().mockResolvedValue({ mock_test_id: "mock-1", report });
    api.deletePendingAudio.mockReset().mockResolvedValue(undefined);
  });

  it("shows the optional practice goal and sends it to the start endpoint", async () => {
    const user = userEvent.setup();
    render(<FullMockTestPage onResult={vi.fn()} />);
    await user.type(screen.getByLabelText("Practice goal"), "technology and environment");
    await user.click(screen.getByRole("button", { name: "Start Practice" }));
    await screen.findByText("Part 1 1/6");
    expect(api.startMockTest).toHaveBeenCalledWith("technology and environment");
  });

  it("starts at 1/4, requires a recording, and preserves completed progress on Previous", async () => {
    const user = userEvent.setup();
    render(<FullMockTestPage onResult={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Start Practice" }));

    expect(await screen.findByText("Part 1 1/6")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Next Question" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Record answer" }));
    await user.click(screen.getByRole("button", { name: "Next Question" }));
    expect(await screen.findByText("Part 1 2/6")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Record answer" }));
    await user.click(screen.getByRole("button", { name: "Next Question" }));
    expect(await screen.findByText("Part 1 3/6")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Previous" }));
    expect(await screen.findByText("Part 1 2/6")).toBeInTheDocument();
  });

  it("submits the final report only after all eight answers are completed", async () => {
    const user = userEvent.setup();
    const onResult = vi.fn();
    render(<FullMockTestPage onResult={onResult} />);
    await user.click(screen.getByRole("button", { name: "Start Practice" }));
    await screen.findByText("Part 1 1/6");

    for (let index = 0; index < questions.length; index += 1) {
      await user.click(screen.getByRole("button", { name: "Record answer" }));
      if (index < questions.length - 1) {
        await user.click(screen.getByRole("button", { name: "Next Question" }));
        await screen.findByText(`${index + 2} of 11`);
      } else {
        await user.click(screen.getByRole("button", { name: "Finish Test (10/11)" }));
      }
    }

    await waitFor(() => expect(api.evaluateMockTest).toHaveBeenCalledOnce());
    expect(api.evaluateMockTest.mock.calls[0][0]).toHaveLength(11);
    expect(onResult).toHaveBeenCalledWith(expect.objectContaining({ mockTestId: "mock-1", report }));
  });
});
