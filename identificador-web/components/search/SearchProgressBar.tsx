"use client";

import { formatPollDuration } from "@/lib/pollConfig";
import type { ProgressPhase, SearchProgress } from "@/lib/search/types";

export function SearchProgressBar({
  progress,
  phase,
  secondsRemaining,
  onStop,
}: {
  progress: SearchProgress;
  phase: ProgressPhase;
  secondsRemaining: number | null;
  onStop?: () => void;
}) {
  const { processed, total } = progress;
  const hasTotal = total > 0;
  const percent = hasTotal
    ? Math.min(100, Math.round((processed / total) * 100))
    : 0;

  const label =
    phase === "deep"
      ? hasTotal
        ? `Búsqueda profunda (${processed}/${total})`
        : "Iniciando búsqueda profunda..."
      : hasTotal
        ? `Analizando publicaciones (${processed}/${total})`
        : "Buscando coincidencias en la imagen...";

  return (
    <div className="mt-4 w-full" aria-live="polite">
      <div className="flex items-center justify-between gap-3 mb-2">
        <p className="text-sm text-neutral-600 dark:text-neutral-400">
          {label}
        </p>
        <div className="flex items-center gap-3 shrink-0">
          {secondsRemaining !== null && (
            <span className="text-sm tabular-nums text-neutral-500 dark:text-neutral-400">
              {formatPollDuration(secondsRemaining)} restantes
            </span>
          )}
          {hasTotal && (
            <span className="text-sm font-medium tabular-nums">{percent}%</span>
          )}
        </div>
      </div>
      <div
        className="h-2 w-full overflow-hidden rounded-full bg-neutral-200 dark:bg-neutral-800"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={hasTotal ? total : undefined}
        aria-valuenow={hasTotal ? processed : undefined}
        aria-label={label}
      >
        {hasTotal ? (
          <div
            className="h-full rounded-full bg-neutral-900 dark:bg-neutral-100 transition-[width] duration-300 ease-out"
            style={{ width: `${percent}%` }}
          />
        ) : (
          <div
            className="h-full w-1/4 rounded-full bg-neutral-900 dark:bg-neutral-100"
            style={{
              animation: "progress-indeterminate 1.4s ease-in-out infinite",
            }}
          />
        )}
      </div>
      {onStop && (
        <button
          type="button"
          onClick={onStop}
          className="mt-3 text-sm text-neutral-600 dark:text-neutral-400 underline-offset-2 hover:underline"
        >
          Mostrar resultados parciales
        </button>
      )}
    </div>
  );
}
