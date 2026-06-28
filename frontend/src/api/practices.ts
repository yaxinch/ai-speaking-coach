import { apiRequest } from "./client";
import type { PracticeDetail, PracticeSummary } from "../types/practice";

export function listPractices(): Promise<PracticeSummary[]> {
  return apiRequest<PracticeSummary[]>("/api/practices");
}

export function getPractice(id: string): Promise<PracticeDetail> {
  return apiRequest<PracticeDetail>(`/api/practices/${id}`);
}
