// api/schemas/* と対応する型定義

export type Label = "loved" | "completed" | "dropped";

export interface ResponseInput {
  anime_id: number;
  label: Label;
}

export interface QuestionItem {
  anime_id: number;
  title: string;
  year: number | null;
  episodes: number | null;
  genres: string[];
  completion_rate: number | null;
  split_score: number | null;
  in_pool: boolean;
}

export interface QuestionsResponse {
  items: QuestionItem[];
  total: number;
  limit: number;
  offset: number;
}

export type SortOption = "split_score" | "popularity" | "low_completion" | "year_desc";

export interface Reason {
  type: string;
  text: string;
}

export interface CurvePoint {
  range: string;
  user: number;
  avg: number;
}

export interface EpisodeBucket {
  range: string;
  completion_rate: number | null;
  count: number;
}

export interface ProfileOut {
  type_name: string;
  endurance_episodes: number | null;
  episode_buckets: EpisodeBucket[];
  best_episode_bucket: EpisodeBucket | null;
  completion_rate: number | null;
  completion_rate_avg: number;
  preferred_genres: string[];
  avoided_genres: string[];
  curve: CurvePoint[];
}

export interface AtRiskItem {
  anime_id: number;
  title: string;
  year: number | null;
  episodes: number | null;
  genres: string[];
  completion_prob: number;
  population_completion_rate: number;
  relative_risk: number | null;
  popularity_rank: number | null;
  is_ongoing: boolean;
  reasons: Reason[];
}

export interface WillCompleteItem {
  anime_id: number;
  title: string;
  year: number | null;
  episodes: number | null;
  genres: string[];
  completion_prob: number;
  population_completion_rate: number;
  relative_completion: number | null;
  is_ongoing: boolean;
  reason: string;
}

export interface BaselineItem {
  anime_id: number;
  title: string;
  is_at_risk: boolean;
}

export interface BaselineComparison {
  popular: BaselineItem[];
  personalized: BaselineItem[];
  overlap: number;
}

export interface PredictResponse {
  profile: ProfileOut;
  at_risk: AtRiskItem[];
  at_risk_threshold: number;
  will_complete: WillCompleteItem[];
  baseline_comparison: BaselineComparison;
}

export type Confidence = "high" | "medium" | "low";

export interface AnimeMeta {
  title: string;
  episodes: number | null;
  genres: string[];
  year: number | null;
}

export interface Factors {
  negative: Reason[];
  positive: Reason[];
}

export interface EvidenceItem {
  title: string;
  episodes: number | null;
  genre: string | null;
  result: "completed" | "dropped";
}

export interface DropoutCurvePoint {
  episode: number;
  rate: number;
}

export interface NextRecommendation {
  anime_id: number;
  title: string;
  completion_prob: number;
}

export interface PredictSingleResponse {
  anime: AnimeMeta;
  completion_prob: number;
  population_completion_rate: number;
  relative_risk: number | null;
  confidence: Confidence;
  is_estimated: boolean;
  is_ongoing: boolean;
  factors: Factors;
  evidence: EvidenceItem[];
  evidence_insight: string | null;
  dropout_curve: DropoutCurvePoint[] | null;
  peak_dropout_episode: number | null;
  survival_after_peak: number | null;
  insufficient_data: boolean;
  advice: string;
  next_recommendations: NextRecommendation[];
}

export interface AlreadyAnsweredResponse {
  already_answered: true;
  anime_id: number;
  label: string;
  message: string;
}

export type PredictSingleResult = PredictSingleResponse | AlreadyAnsweredResponse;

export function isAlreadyAnswered(
  result: PredictSingleResult,
): result is AlreadyAnsweredResponse {
  return (result as AlreadyAnsweredResponse).already_answered === true;
}
