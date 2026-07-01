import { forwardRef, useImperativeHandle } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { PartType, SectionPracticeStart } from "../types/practice";
import { PracticePage, sectionSelectionToQuestion } from "./PracticePage";
import { TargetedPracticePage } from "./TargetedPracticePage";

const api = vi.hoisted(() => ({ startSectionPractice: vi.fn() }));

vi.mock("../api/practices", () => ({ startSectionPractice: api.startSectionPractice }));
vi.mock("../api/speaking", () => ({ submitVoiceAnswer: vi.fn(), voiceResultToFeedback: vi.fn() }));
vi.mock("../hooks/useExaminerVoice", () => ({
  useExaminerVoice: () => ({ voices: {}, play: vi.fn(), stop: vi.fn(), clear: vi.fn() })
}));
vi.mock("../components/SpokenQuestionCard", () => ({
  SpokenQuestionCard: ({ question }: { question: { question: string } }) => <div>Prompt: {question.question}</div>
}));
vi.mock("../components/VoiceAnswerRecorder", () => ({
  VoiceAnswerRecorder: forwardRef(function Recorder(_, ref) {
    useImperativeHandle(ref, () => ({ stopPlayback: vi.fn() }));
    return <div>Recorder</div>;
  })
}));

function selection(part: PartType, id = `${part}-1`): SectionPracticeStart {
  const isPart2 = part === "part2";
  return {
    selectionId: `selection-${id}`,
    mode: "goal_based",
    practiceGoal: "technology",
    part,
    item: {
      type: isPart2 ? "part2_cue_card" : `${part}_question` as "part1_question" | "part3_question",
      id,
      topic: "technology",
      text: isPart2 ? "Describe useful technology" : `${part} technology question?`,
      source: "Reviewed practice source",
      difficulty: "medium",
      cueCard: isPart2
        ? {
            id,
            topic: "technology",
            prompt: "Describe useful technology",
            bulletPoints: ["what it is", "why it is useful"],
            preparationTimeSeconds: 60,
            speakingTimeSeconds: 120,
            source: "Reviewed practice source",
            difficulty: "medium"
          }
        : null
    },
    metadata: {
      retrievalUsed: true,
      candidateCount: 10,
      selectorUsed: true,
      fallbackUsed: false,
      fallbackReason: null,
      createdAt: "2026-07-01T00:00:00Z"
    }
  };
}

describe("TargetedPracticePage", () => {
  beforeEach(() => api.startSectionPractice.mockReset());

  it("requires a part and sends the optional goal before entering practice", async () => {
    const user = userEvent.setup();
    const onStart = vi.fn();
    api.startSectionPractice.mockResolvedValue(selection("part1"));
    render(<TargetedPracticePage onStart={onStart} />);

    await user.click(screen.getByRole("button", { name: "Start Practice" }));
    expect(await screen.findByText("Please choose an IELTS Speaking part.")).toBeInTheDocument();

    await user.click(screen.getByText("Part 1"));
    await user.type(screen.getByLabelText("Practice goal"), "technology");
    await user.click(screen.getByRole("button", { name: "Start Practice" }));
    await waitFor(() => expect(api.startSectionPractice).toHaveBeenCalledWith("part1", "technology"));
    expect(onStart).toHaveBeenCalledWith("part1", "technology", expect.objectContaining({ selectionId: "selection-part1-1" }));
  });
});

describe("PracticePage section selection", () => {
  beforeEach(() => api.startSectionPractice.mockReset());

  it("maps all part types to the existing single-question transport", () => {
    expect(sectionSelectionToQuestion(selection("part1")).cue_card).toBeNull();
    expect(sectionSelectionToQuestion(selection("part3")).part_type).toBe("part3");
    const part2 = sectionSelectionToQuestion(selection("part2"));
    expect(part2.cue_card?.bullet_points).toEqual(["what it is", "why it is useful"]);
    expect(part2.bank_question_id).toBe("part2-1");
  });

  it("regenerates with the same part and practice goal", async () => {
    const user = userEvent.setup();
    api.startSectionPractice.mockResolvedValue(selection("part1", "part1-2"));
    render(
      <PracticePage
        partType="part1"
        practiceGoal="technology"
        initialSelection={selection("part1")}
        onBack={vi.fn()}
        onResult={vi.fn()}
      />
    );
    expect(screen.getByText("Prompt: part1 technology question?")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Regenerate Question" }));
    await waitFor(() => expect(api.startSectionPractice).toHaveBeenCalledWith("part1", "technology"));
    expect(await screen.findByText("Prompt: part1 technology question?")).toBeInTheDocument();
  });
});
