import { apiEmptyRequest, apiRequest } from "./client";
import type { PartType, PracticeDetail, PracticeSummary, SectionPracticeStart } from "../types/practice";

export function startSectionPractice(part: PartType, practiceGoal: string): Promise<SectionPracticeStart> {
  return apiRequest<SectionPracticeStart>("/api/practices/section/start", {
    method: "POST",
    body: JSON.stringify({ part, practiceGoal })
  });
}

export function listPractices(): Promise<PracticeSummary[]> {
  return apiRequest<PracticeSummary[]>("/api/practices");
}

export function getPractice(id: string): Promise<PracticeDetail> {
  return apiRequest<PracticeDetail>(`/api/practices/${id}`);
}

export function deletePractice(id: string): Promise<void> {
  return apiEmptyRequest(`/api/practices/${id}`, { method: "DELETE" });
}
