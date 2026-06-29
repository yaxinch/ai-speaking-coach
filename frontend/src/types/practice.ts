export type PartType = "part1" | "part2" | "part3";

export interface CueCard {
  topic: string;
  bullet_points: string[];
  preparation_instruction: string;
}

export interface ExaminerQuestion {
  part_type: PartType;
  question: string;
  cue_card: CueCard | null;
}

export interface PracticeSummary {
  id: string;
  part_type: PartType;
  question_text: string;
  overall_band: number | null;
  created_at: string;
}

export interface PracticeDetail {
  id: string;
  part_type: PartType;
  question: ExaminerQuestion;
  question_text: string;
  user_answer: string;
  feedback: FeedbackResult;
  overall_band: number | null;
  created_at: string;
}

export interface FeedbackResult {
  overall_band_score: number | null;
  fluency_score: number | null;
  vocabulary_score: number | null;
  grammar_score: number | null;
  pronunciation_note: string;
  strengths: string[];
  weaknesses: string[];
  improved_answer: string;
  action_suggestions: string[];
}

export type PracticeMode = "targeted" | "full_mock";

export interface MockQuestion extends ExaminerQuestion {
  question_index: number;
}

export interface MockAnswer {
  part_type: PartType;
  question_index: number;
  question: MockQuestion;
  answer_text: string;
  audio_url: string | null;
  transcript_text: string | null;
}

export interface QuestionAnalysis {
  question_index: number;
  band_estimate: number | null;
  feedback: string;
  strengths: string[];
  weaknesses: string[];
  improved_answer: string;
}

export interface PartFeedback {
  band_estimate: number | null;
  summary: string;
  strengths: string[];
  weaknesses: string[];
  question_analyses: QuestionAnalysis[];
}

export interface MockTestReport {
  overall_band_score: number | null;
  key_strengths: string[];
  key_weaknesses: string[];
  action_plan: string[];
  part1_feedback: PartFeedback;
  part2_feedback: PartFeedback;
  part3_feedback: PartFeedback;
}

export interface MockTestSummary {
  id: string;
  mode: "full_mock";
  overall_band: number | null;
  created_at: string;
}

export interface MockTestDetail extends MockTestSummary {
  questions: MockQuestion[];
  answers: MockAnswer[];
  report: MockTestReport;
}

export type HistoryEntry =
  | (PracticeSummary & { mode: "targeted" })
  | MockTestSummary;
