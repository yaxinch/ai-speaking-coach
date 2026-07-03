import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { MockAnswer, MockTestReport, PartFeedback } from "../types/practice";
import { MockTestReportView } from "./MockTestReportView";

const emptyPart: PartFeedback = {
  band_estimate: 6.5,
  summary: "Part summary that belongs on the part tab.",
  strengths: ["Part strength"],
  weaknesses: ["Part weakness"],
  question_analyses: []
};

const report: MockTestReport = {
  overall_band_score: 6.5,
  criteria_scores: {
    fluency_coherence: 6,
    lexical_resource: 6.5,
    grammatical_range_accuracy: 6.5,
    pronunciation: 7
  },
  overall_feedback: "Long aggregated overall feedback.",
  key_strengths: ["Overall strength"],
  key_weaknesses: ["Overall weakness"],
  action_plan: ["Action plan"],
  next_practice_focus: ["Practice focus"],
  repeated_errors: [{ error_type: "Grammar", examples: ["Example"], suggestion: "Suggestion" }],
  part_performance: { part1: "Part 1 performance", part2: "Part 2 performance", part3: "Part 3 performance" },
  part1_feedback: emptyPart,
  part2_feedback: emptyPart,
  part3_feedback: emptyPart
};

const answer: MockAnswer = {
  part_type: "part1",
  question_index: 1,
  question: { part_type: "part1", question_index: 1, question: "Do you work or study?", cue_card: null },
  answer_text: "I work as a developer.",
  transcript_text: "I work as a developer.",
  audio_url: null,
  voice_score: {
    overall: 6.5,
    fluency_coherence: 6,
    lexical_resource: 6.5,
    grammatical_range_accuracy: 6.5,
    pronunciation: 7
  },
  voice_feedback: null
};

describe("MockTestReportView", () => {
  it("keeps the overview score-only", () => {
    render(<MockTestReportView report={report} answers={[]} />);

    expect(screen.getByText("Overall band estimate")).toBeInTheDocument();
    expect(screen.getByText("Fluency & Coherence")).toBeInTheDocument();
    expect(screen.queryByText("Long aggregated overall feedback.")).not.toBeInTheDocument();
    expect(screen.queryByText("Key Strengths")).not.toBeInTheDocument();
    expect(screen.queryByText("Key Weaknesses")).not.toBeInTheDocument();
    expect(screen.queryByText("Next Practice Focus")).not.toBeInTheDocument();
    expect(screen.queryByText("Repeated Errors")).not.toBeInTheDocument();
    expect(screen.queryByText("Part Performance")).not.toBeInTheDocument();
  });

  it("shows only the part band before the question results", async () => {
    const user = userEvent.setup();
    render(<MockTestReportView report={report} answers={[answer]} />);

    await user.click(screen.getByRole("tab", { name: "Part 1" }));
    expect(screen.getByText("Band estimate")).toBeInTheDocument();
    expect(screen.queryByText("Part 1 Feedback")).not.toBeInTheDocument();
    expect(screen.queryByText("Part summary that belongs on the part tab.")).not.toBeInTheDocument();
    expect(screen.queryByText("Strengths")).not.toBeInTheDocument();
    expect(screen.queryByText("Weaknesses")).not.toBeInTheDocument();
    expect(screen.queryByText("Part strength")).not.toBeInTheDocument();
    expect(screen.queryByText("Part weakness")).not.toBeInTheDocument();
    expect(screen.queryByText("Band N/A")).not.toBeInTheDocument();
    const overallCard = screen.getByTestId("overall-score-card");
    expect(overallCard).toHaveAttribute("data-score-variant", "primary");
    expect(within(overallCard).getByText("6.5")).toBeInTheDocument();
  });
});
