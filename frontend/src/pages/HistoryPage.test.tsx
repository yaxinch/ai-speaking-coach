import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { HistoryPage } from "./HistoryPage";

const api = vi.hoisted(() => ({
  listPractices: vi.fn(),
  deletePractice: vi.fn(),
  listMockTests: vi.fn(),
  deleteMockTest: vi.fn()
}));

vi.mock("../api/practices", () => ({
  listPractices: api.listPractices,
  deletePractice: api.deletePractice
}));

vi.mock("../api/mockTests", () => ({
  listMockTests: api.listMockTests,
  deleteMockTest: api.deleteMockTest
}));

describe("HistoryPage", () => {
  beforeEach(() => {
    api.listPractices.mockReset().mockResolvedValue([
      {
        id: "practice-1",
        part_type: "part1",
        question_text: "Do you work or study?",
        overall_band: 6.5,
        created_at: "2026-07-01T10:00:00Z"
      }
    ]);
    api.listMockTests.mockReset().mockResolvedValue([
      { id: "mock-1", mode: "full_mock", overall_band: 7, created_at: "2026-07-01T11:00:00Z" }
    ]);
    api.deletePractice.mockReset().mockResolvedValue(undefined);
    api.deleteMockTest.mockReset().mockResolvedValue(undefined);
  });

  it("bulk deletes selected targeted and full mock history records", async () => {
    const user = userEvent.setup();
    render(<HistoryPage onOpen={vi.fn()} />);

    await screen.findByText(/Do you work or study\?/);
    await user.click(screen.getByRole("button", { name: "Select History to Delete" }));
    await user.click(screen.getByRole("checkbox", { name: "Select targeted practice" }));
    await user.click(screen.getByRole("checkbox", { name: "Select full mock test" }));
    await user.click(screen.getByRole("button", { name: "Delete Selected" }));
    await user.click(screen.getByRole("button", { name: "Delete" }));

    await waitFor(() => {
      expect(api.deletePractice).toHaveBeenCalledWith("practice-1");
      expect(api.deleteMockTest).toHaveBeenCalledWith("mock-1");
    });
    expect(await screen.findByText("No practice records yet.")).toBeInTheDocument();
  });
});
