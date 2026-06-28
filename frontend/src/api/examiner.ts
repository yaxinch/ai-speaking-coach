import { apiRequest } from "./client";
import type { ExaminerQuestion, PartType } from "../types/practice";

export function generateQuestion(partType: PartType): Promise<ExaminerQuestion> {
  return apiRequest<ExaminerQuestion>("/api/examiner/generate", {
    method: "POST",
    body: JSON.stringify({ part_type: partType })
  });
}
