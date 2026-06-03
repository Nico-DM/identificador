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
