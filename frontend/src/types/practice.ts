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
