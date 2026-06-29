import { apiRequest } from "./client";
import type { MockAnswer, MockQuestion, MockTestDetail, MockTestReport, MockTestSummary } from "../types/practice";

export function generateMockTest(): Promise<{ questions: MockQuestion[] }> {
  return apiRequest("/api/mock-tests/generate", { method: "POST" });
}

export function evaluateMockTest(
  answers: MockAnswer[]
): Promise<{ mock_test_id: string; report: MockTestReport }> {
  return apiRequest("/api/mock-tests/evaluate", {
    method: "POST",
    body: JSON.stringify({ answers })
  });
}

export function listMockTests(): Promise<MockTestSummary[]> {
  return apiRequest("/api/mock-tests");
}

export function getMockTest(id: string): Promise<MockTestDetail> {
  return apiRequest(`/api/mock-tests/${id}`);
}
