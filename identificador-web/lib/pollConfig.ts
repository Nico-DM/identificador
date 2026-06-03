const DEFAULT_POLL_MAX_ATTEMPTS = 60;
const DEFAULT_POLL_DELAY_MS = 2000;

function parsePositiveInt(value: string | undefined, fallback: number): number {
  if (!value?.trim()) return fallback;
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) return fallback;
  return parsed;
}

/** Intentos de polling antes de mostrar resultados parciales o error por timeout. */
export const POLL_MAX_ATTEMPTS = parsePositiveInt(
  process.env.NEXT_PUBLIC_POLL_MAX_ATTEMPTS,
  DEFAULT_POLL_MAX_ATTEMPTS,
);

/** Pausa entre consultas a /api/results (ms). */
export const POLL_DELAY_MS = parsePositiveInt(
  process.env.NEXT_PUBLIC_POLL_DELAY_MS,
  DEFAULT_POLL_DELAY_MS,
);

/** Tiempo máximo de espera del polling (s), derivado de intentos × intervalo. */
export const POLL_TIMEOUT_SECONDS = Math.ceil(
  (POLL_MAX_ATTEMPTS * POLL_DELAY_MS) / 1000,
);

export const POLL_TIMEOUT_OPTIONS = [
  { label: "30 s", seconds: 30 },
  { label: "1 min", seconds: 60 },
  { label: "2 min", seconds: 120 },
  { label: "5 min", seconds: 300 },
  { label: "10 min", seconds: 600 },
] as const;

export const DEFAULT_POLL_TIMEOUT_SECONDS = 120;

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
