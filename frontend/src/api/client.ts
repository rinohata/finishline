import type {
  PredictResponse,
  PredictSingleResult,
  QuestionsResponse,
  ResponseInput,
  SortOption,
} from "./types";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`API error ${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export interface QuestionsParams {
  q?: string;
  genre?: string[];
  year_from?: number;
  year_to?: number;
  episodes_max?: number;
  sort?: SortOption;
  limit?: number;
  offset?: number;
}

export function fetchQuestions(params: QuestionsParams): Promise<QuestionsResponse> {
  const search = new URLSearchParams();
  if (params.q) search.set("q", params.q);
  if (params.genre) for (const g of params.genre) search.append("genre", g);
  if (params.year_from != null) search.set("year_from", String(params.year_from));
  if (params.year_to != null) search.set("year_to", String(params.year_to));
  if (params.episodes_max != null) search.set("episodes_max", String(params.episodes_max));
  if (params.sort) search.set("sort", params.sort);
  search.set("limit", String(params.limit ?? 20));
  search.set("offset", String(params.offset ?? 0));
  return request<QuestionsResponse>(`/questions?${search.toString()}`);
}

export function postPredict(responses: ResponseInput[]): Promise<PredictResponse> {
  return request<PredictResponse>("/predict", {
    method: "POST",
    body: JSON.stringify({ responses }),
  });
}

export function postPredictSingle(
  responses: ResponseInput[],
  targetAnimeId: number,
): Promise<PredictSingleResult> {
  return request<PredictSingleResult>("/predict/single", {
    method: "POST",
    body: JSON.stringify({ responses, target_anime_id: targetAnimeId }),
  });
}
