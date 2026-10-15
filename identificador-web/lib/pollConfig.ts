const DEFAULT_POLL_DELAY_MS = 2000;
/** Safety ceiling so the client does not poll forever if the backend stalls. */
const DEFAULT_SAFETY_POLL_TIMEOUT_SECONDS = 1800;

function parsePositiveInt(value: string | undefined, fallback: number): number {
  if (!value?.trim()) return fallback;
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) return fallback;
  return parsed;
}

/** Delay between /api/results polls (ms). */
export const POLL_DELAY_MS = parsePositiveInt(
  process.env.NEXT_PUBLIC_POLL_DELAY_MS,
  DEFAULT_POLL_DELAY_MS,
);

export const SAFETY_POLL_TIMEOUT_SECONDS = parsePositiveInt(
  process.env.NEXT_PUBLIC_SAFETY_POLL_TIMEOUT_SECONDS,
  DEFAULT_SAFETY_POLL_TIMEOUT_SECONDS,
);

export const BATCH_SIZE_OPTIONS = [
  { label: "5", size: 5 },
  { label: "10", size: 10 },
  { label: "15", size: 15 },
  { label: "20", size: 20 },
] as const;

export const DEFAULT_BATCH_SIZE = 10;

export function pollAttemptsForTimeout(timeoutSeconds: number): number {
  return Math.max(1, Math.ceil((timeoutSeconds * 1000) / POLL_DELAY_MS));
}

export function formatPollDuration(totalSeconds: number): string {
  const seconds = Math.max(0, Math.round(totalSeconds));
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  if (minutes === 0) return `${remainder} s`;
  if (remainder === 0) return `${minutes} min`;
  return `${minutes} min ${remainder} s`;
}
