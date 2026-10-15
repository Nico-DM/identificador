export type ResultConfidence = "confirmed" | "provisional" | "pending";

export type SearchResult = {
  date: string | null;
  platform: string | null;
  url: string;
  score: number | null;
  source: string;
  confidence?: ResultConfidence;
  thumbnail?: string | null;
  favicon?: string | null;
  site_name?: string | null;
};

export type BatchInfo = {
  size: number;
  processed_candidates: number;
  total_candidates: number;
  remaining: number;
};

export type ResultsPayload = {
  status?: string;
  results?: SearchResult[];
  error?: string;
  detail?: string;
  progress?: { processed?: number; total?: number };
  batch?: BatchInfo;
};

export type SearchProgress = {
  processed: number;
  total: number;
};

export type ProgressPhase = "static" | "deep" | "reverse_image";

export type InputMode = "url" | "file";

export type PollOutcome = "done" | "error" | "timeout" | "partial";
