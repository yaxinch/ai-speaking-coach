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
  answer_source?: "text" | "voice";
  transcript_text?: string | null;
  audio_asset_id?: string | null;
  audio_url?: string | null;
}

export interface Correction {
  original: string;
  corrected: string;
  reason: string;
}

export interface WeakPronunciationWord {
  word: string;
  accuracy_score: number;
  error_type: string | null;
}

export interface PronunciationAssessment {
  available: boolean;
  provider: string;
  is_mock: boolean;
  pron_score: number | null;
  estimated_ielts_band: number | null;
  accuracy_score: number | null;
  fluency_score: number | null;
  prosody_score: number | null;
  weak_words: WeakPronunciationWord[];
  message: string;
}

export interface FeedbackResult {
  overall_band_score: number | null;
  fluency_score: number | null;
  vocabulary_score: number | null;
  grammar_score: number | null;
  pronunciation_score?: number | null;
  pronunciation_note: string;
  pronunciation_assessment?: PronunciationAssessment | null;
  summary?: string;
  strengths: string[];
  weaknesses: string[];
  corrections?: Correction[];
  improved_answer: string;
  action_suggestions: string[];
  next_practice_suggestion?: string;
}

export interface VoiceScore {
  overall: number | null;
  fluency_coherence: number | null;
  lexical_resource: number | null;
  grammatical_range_accuracy: number | null;
  pronunciation: number | null;
  pronunciation_assessment?: PronunciationAssessment | null;
}

export interface VoiceFeedback {
  summary: string;
  strengths: string[];
  weaknesses: string[];
  corrections: Correction[];
  improved_answer: string;
  next_practice_suggestion: string;
  pronunciation_note: string;
}

export interface VoiceAnswerResult {
  practice_id: string | null;
  audio_asset_id: string;
  audio_url: string;
  transcript: string;
  asr_provider: string;
  is_mock_transcript: boolean;
  score: VoiceScore;
  feedback: VoiceFeedback;
}

export interface VoiceAnswerValue {
  audioBlob?: Blob;
  audioUrl?: string;
  duration?: number;
  mimeType?: string;
  recordedAt?: string;
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
  audio_asset_id?: string | null;
  transcript_text: string | null;
  voice_score?: VoiceScore | null;
  voice_feedback?: VoiceFeedback | null;
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
