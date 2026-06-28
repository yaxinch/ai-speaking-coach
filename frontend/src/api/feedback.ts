import { apiRequest } from "./client";
import type { ExaminerQuestion, FeedbackResult, PartType } from "../types/practice";

export interface EvaluateResponse {
  practice_id: string;
  feedback: FeedbackResult;
}

export function evaluateAnswer(
  partType: PartType,
  question: ExaminerQuestion,
  userAnswer: string
): Promise<EvaluateResponse> {
  return apiRequest<EvaluateResponse>("/api/feedback/evaluate", {
    method: "POST",
    body: JSON.stringify({
      part_type: partType,
      question,
      user_answer: userAnswer
    })
  });
}
