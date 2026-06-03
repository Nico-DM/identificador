"use client";
import { useEffect, useRef, useState } from "react";
import { clientImageUrlRejectionMessage } from "@/lib/imageUrl";
import {
  DEFAULT_POLL_TIMEOUT_SECONDS,
  formatPollDuration,
  POLL_DELAY_MS,
  POLL_TIMEOUT_OPTIONS,
  pollAttemptsForTimeout,
} from "@/lib/pollConfig";

type ResultConfidence = "confirmed" | "provisional" | "pending";

type SearchResult = {
  date: string | null;
  platform: string | null;
  url: string;
  score: number | null;
  source: string;
  confidence?: ResultConfidence;
  thumbnail?: string | null;
  site_name?: string | null;
};

type PollTarget = "static" | "deep";

type DeepSearchInfo = {
  available: boolean;
  pending_urls: number;
};

type ResultsPayload = {
  status?: string;
  results?: SearchResult[];
  error?: string;
  detail?: string;
  progress?: { processed?: number; total?: number };
  deep_search?: DeepSearchInfo;
};

function formatDate(iso: string | null): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString("es-ES", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function siteInitials(siteName: string): string {
  const cleaned = siteName.replace(/^www\./, "").split(".")[0] ?? siteName;
  return cleaned.slice(0, 2).toUpperCase();
}

type SearchProgress = {
  processed: number;
  total: number;
};

type ProgressPhase = "static" | "deep" | "serpapi";

function abortableDelay(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("Aborted", "AbortError"));
      return;
    }
    const timer = window.setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        window.clearTimeout(timer);
        reject(new DOMException("Aborted", "AbortError"));
      },
      { once: true },
    );
  });
}

function SearchProgressBar({
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
    <div className="mt-4 w-full" role="status" aria-live="polite">
      <div className="flex items-center justify-between gap-3 mb-2">
        <p className="text-sm text-neutral-600 dark:text-neutral-400">{label}</p>
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
            style={{ animation: "progress-indeterminate 1.4s ease-in-out infinite" }}
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

function ResultCard({ result }: { result: SearchResult }) {
  const [imageError, setImageError] = useState(false);
  const siteName = result.site_name ?? result.platform ?? result.url;
  const showThumbnail = result.thumbnail && !imageError;
  const confidence = result.confidence ?? (result.date ? "confirmed" : "pending");
  const formattedDate = formatDate(result.date);

  return (
    <article className="flex flex-col gap-2">
      <a
        href={result.url}
        target="_blank"
        rel="noopener noreferrer"
        className="block overflow-hidden rounded-lg border border-neutral-200 dark:border-neutral-700 hover:opacity-90 transition-opacity"
      >
        {showThumbnail ? (
          // biome-ignore lint/performance/noImgElement: thumbnails from external SerpApi domains
          <img
            src={result.thumbnail ?? undefined}
            alt={`Vista previa de ${siteName}`}
            loading="lazy"
            width={200}
            height={200}
            className="w-full aspect-square object-cover bg-neutral-100 dark:bg-neutral-800"
            onError={() => setImageError(true)}
          />
        ) : (
          <div className="w-full aspect-square flex items-center justify-center bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400 text-2xl font-semibold">
            {siteInitials(siteName)}
          </div>
        )}
      </a>
      <div className="px-1">
        <a
          href={result.url}
          target="_blank"
          rel="noopener noreferrer"
          className="font-medium text-sm hover:underline line-clamp-2"
        >
          {siteName}
        </a>
        {formattedDate && (
          <p
            className={`text-xs mt-0.5 ${
              confidence === "provisional"
                ? "text-amber-600 dark:text-amber-400"
                : "text-neutral-500 dark:text-neutral-400"
            }`}
          >
            {formattedDate}
            {confidence === "provisional" && " · fecha aproximada"}
          </p>
        )}
      </div>
    </article>
  );
}


export default function Home() {
  const [imageUrl, setImageUrl] = useState("");
  const [searchedImageUrl, setSearchedImageUrl] = useState<string | null>(null);
  const [queryImageError, setQueryImageError] = useState(false);
  const [loading, setLoading] = useState(false);
  const [deepLoading, setDeepLoading] = useState(false);
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchId, setSearchId] = useState<string | null>(null);
  const [deepSearch, setDeepSearch] = useState<DeepSearchInfo | null>(null);
  const [progressPhase, setProgressPhase] = useState<ProgressPhase>("serpapi");
  const [progress, setProgress] = useState<SearchProgress>({
    processed: 0,
    total: 0,
  });
  const [safeSearchEnabled, setSafeSearchEnabled] = useState(true);
  const [pollTimeoutSeconds, setPollTimeoutSeconds] = useState(
    DEFAULT_POLL_TIMEOUT_SECONDS,
  );
  const [canRetryPoll, setCanRetryPoll] = useState(false);
  const [pollTarget, setPollTarget] = useState<PollTarget>("static");
  const [retryingPoll, setRetryingPoll] = useState(false);
  const [pollSecondsRemaining, setPollSecondsRemaining] = useState<number | null>(
    null,
  );
  const [pollStoppedByUser, setPollStoppedByUser] = useState(false);
  const pollAbortRef = useRef<AbortController | null>(null);

  const clearStaleFormState = () => {
    setImageUrl("");
    setLoading(false);
  };

  useEffect(() => {
    clearStaleFormState();
    const raf = requestAnimationFrame(clearStaleFormState);
    const t0 = window.setTimeout(clearStaleFormState, 0);
    const t1 = window.setTimeout(clearStaleFormState, 100);

    const onPageShow = (event: PageTransitionEvent) => {
      if (event.persisted) {
        clearStaleFormState();
      }
    };
    window.addEventListener("pageshow", onPageShow);

    return () => {
      cancelAnimationFrame(raf);
      window.clearTimeout(t0);
      window.clearTimeout(t1);
      window.removeEventListener("pageshow", onPageShow);
    };
  }, []);

  const applyResultsPayload = (data: ResultsPayload) => {
    if (data.progress) {
      setProgress({
        processed: data.progress.processed ?? 0,
        total: data.progress.total ?? 0,
      });
    }
    if (Array.isArray(data.results)) {
      setResults(data.results);
    }
    if (data.deep_search) {
      setDeepSearch(data.deep_search);
    }
    if (data.status) {
      setStatus(data.status);
    }
  };

  const beginPollSession = () => {
    pollAbortRef.current?.abort();
    const controller = new AbortController();
    pollAbortRef.current = controller;
    setPollSecondsRemaining(pollTimeoutSeconds);
    setPollStoppedByUser(false);
    return controller.signal;
  };

  const endPollSession = () => {
    pollAbortRef.current = null;
    setPollSecondsRemaining(null);
  };

  const handleStopPoll = () => {
    pollAbortRef.current?.abort();
  };

  const resolveEarlyPoll = (
    data: ResultsPayload,
    lastResults: SearchResult[],
    untilStatuses: string[],
    stoppedByUser: boolean,
  ): "done" | "partial" => {
    if (
      data.status &&
      untilStatuses.includes(data.status) &&
      data.status !== "error"
    ) {
      return "done";
    }

    if (lastResults.length > 0) {
      setResults(lastResults);
    }
    setStatus("partial");
    setError(null);
    setPollStoppedByUser(stoppedByUser);
    setCanRetryPoll(true);
    return "partial";
  };

  const pollResults = async (
    id: string,
    options: {
      untilStatuses: string[];
      onStatus?: (data: ResultsPayload) => void;
      progressPhase?: ProgressPhase;
      signal?: AbortSignal;
    },
  ): Promise<"done" | "error" | "timeout" | "partial"> => {
    const maxAttempts = pollAttemptsForTimeout(pollTimeoutSeconds);
    const delayMs = POLL_DELAY_MS;
    let lastResults: SearchResult[] = [];

    if (options.progressPhase) {
      setProgressPhase(options.progressPhase);
    }

    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      setPollSecondsRemaining(
        Math.max(0, Math.ceil(((maxAttempts - attempt) * delayMs) / 1000)),
      );

      try {
        await abortableDelay(delayMs, options.signal);
      } catch {
        const res = await fetch(`/api/results/${id}`);
        const data: ResultsPayload = await res.json();
        if (res.ok) {
          applyResultsPayload(data);
          if (Array.isArray(data.results) && data.results.length > 0) {
            lastResults = data.results;
          }
          return resolveEarlyPoll(data, lastResults, options.untilStatuses, true);
        }
        setError(data?.detail ?? data?.error ?? "Error consultando resultados");
        setStatus("error");
        return "error";
      }

      const res = await fetch(`/api/results/${id}`);
      const data: ResultsPayload = await res.json();

      if (!res.ok) {
        setError(data?.detail ?? data?.error ?? "Error consultando resultados");
        setStatus("error");
        return "error";
      }

      applyResultsPayload(data);
      options.onStatus?.(data);

      if (Array.isArray(data.results) && data.results.length > 0) {
        lastResults = data.results;
      }

      if (data.status && options.untilStatuses.includes(data.status)) {
        if (data.status === "error") {
          if (lastResults.length > 0) {
            setResults(lastResults);
            setStatus("partial");
            setError(
              "Error en el procesamiento. Se muestran los resultados obtenidos hasta el momento.",
            );
            return "partial";
          }
          setError(data.error ?? "Error en el procesamiento");
          setStatus("error");
          return "error";
        }
        return "done";
      }

      if (data.status === "error") {
        if (lastResults.length > 0) {
          setResults(lastResults);
          setStatus("partial");
          setError(
            "Error en el procesamiento. Se muestran los resultados obtenidos hasta el momento.",
          );
          return "partial";
        }
        setError(data.error ?? "Error en el procesamiento");
        setStatus("error");
        return "error";
      }
    }

    setPollSecondsRemaining(0);
    const finalRes = await fetch(`/api/results/${id}`);
    const finalData: ResultsPayload = await finalRes.json();
    if (finalRes.ok) {
      applyResultsPayload(finalData);
      if (finalData.status && options.untilStatuses.includes(finalData.status)) {
        return finalData.status === "error" ? "error" : "done";
      }
      if (Array.isArray(finalData.results) && finalData.results.length > 0) {
        lastResults = finalData.results;
      }
    }

    if (lastResults.length > 0) {
      setResults(lastResults);
      setStatus("partial");
      setError(null);
      setCanRetryPoll(true);
      return "partial";
    }

    setError("Tiempo de espera agotado. Intenta de nuevo.");
    setStatus("error");
    setCanRetryPoll(true);
    return "timeout";
  };

  const runPollForTarget = async (id: string, target: PollTarget) => {
    const signal = beginPollSession();
    const untilStatuses =
      target === "deep" ? ["done"] : ["static_done", "done"];
    const phase: ProgressPhase = target === "deep" ? "deep" : "static";

    if (target === "deep") {
      setDeepLoading(true);
    } else {
      setLoading(true);
    }
    setProgressPhase(phase);

    try {
      const outcome = await pollResults(id, {
        untilStatuses,
        progressPhase: phase,
        signal,
      });
      if (outcome === "timeout" || outcome === "partial") {
        setCanRetryPoll(true);
      }
      return outcome;
    } finally {
      if (target === "deep") {
        setDeepLoading(false);
      } else {
        setLoading(false);
      }
      endPollSession();
    }
  };

  const handleRetryPoll = async () => {
    if (!searchId || retryingPoll) return;

    setRetryingPoll(true);
    setCanRetryPoll(false);
    setError(null);

    try {
      const outcome = await runPollForTarget(searchId, pollTarget);
      if (outcome === "timeout" || outcome === "partial") {
        setCanRetryPoll(true);
      }
    } catch {
      setError("No se pudo conectar con el backend");
      setCanRetryPoll(true);
    } finally {
      setRetryingPoll(false);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!imageUrl.trim()) return;

    const clientMsg = clientImageUrlRejectionMessage(imageUrl);
    if (clientMsg) {
      setError(clientMsg);
      setStatus("error");
      return;
    }

    setLoading(true);
    setDeepLoading(false);
    setResults(null);
    setError(null);
    setStatus("processing");
    setSearchId(null);
    setDeepSearch(null);
    setProgressPhase("serpapi");
    setProgress({ processed: 0, total: 0 });
    setCanRetryPoll(false);
    setPollTarget("static");
    setPollStoppedByUser(false);
    setSearchedImageUrl(imageUrl.trim());
    setQueryImageError(false);

    try {
      const res = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          image_url: imageUrl.trim(),
          safe_search: safeSearchEnabled,
        }),
      });
      const data = await res.json();

      if (!res.ok) {
        const detail = data?.detail;
        const msg =
          typeof detail === "string"
            ? detail
            : Array.isArray(detail)
              ? detail
                  .map((d: { msg?: string }) => d?.msg)
                  .filter(Boolean)
                  .join(" ")
              : (data?.error ?? "Error iniciando busqueda");
        setError(msg);
        setStatus("error");
        return;
      }

      setSearchId(data.search_id ?? null);
      setStatus(data.status ?? "processing");
      setPollTarget("static");

      if (data.search_id) {
        const terminal = data.status === "done" || data.status === "static_done";
        const outcome = terminal
          ? await (async () => {
              const res = await fetch(`/api/results/${data.search_id}`);
              const payload: ResultsPayload = await res.json();
              if (!res.ok) {
                setError(payload?.detail ?? payload?.error ?? "Error consultando resultados");
                setStatus("error");
                return "error" as const;
              }
              applyResultsPayload(payload);
              return payload.status === "error" ? ("error" as const) : ("done" as const);
            })()
          : await runPollForTarget(data.search_id, "static");
        if (outcome === "timeout" || outcome === "partial") {
          setCanRetryPoll(true);
        }
      }
    } catch {
      setError("No se pudo conectar con el backend");
      setStatus("error");
    } finally {
      setLoading(false);
      endPollSession();
    }
  };

  const handleDeepSearch = async () => {
    if (!searchId || !deepSearch?.available || deepLoading) return;

    setDeepLoading(true);
    setError(null);
    setCanRetryPoll(false);
    setPollTarget("deep");
    setPollStoppedByUser(false);

    try {
      const res = await fetch(`/api/search/${searchId}/deep`, { method: "POST" });
      const data = await res.json();

      if (!res.ok) {
        const detail = data?.detail;
        const msg =
          typeof detail === "string"
            ? detail
            : (data?.error ?? "Error iniciando búsqueda profunda");
        setError(msg);
        return;
      }

      setStatus(data.status ?? "deep_processing");
      const outcome = await runPollForTarget(searchId, "deep");
      if (outcome === "timeout" || outcome === "partial") {
        setCanRetryPoll(true);
      }
    } catch {
      setError("No se pudo conectar con el backend");
    } finally {
      setDeepLoading(false);
      endPollSession();
    }
  };

  const showResults =
    (status === "done" ||
      status === "static_done" ||
      status === "partial") &&
    results;

  const showProgress =
    loading ||
    status === "processing" ||
    status === "deep_processing" ||
    deepLoading ||
    retryingPoll;

  const showRetryPollButton =
    canRetryPoll && searchId && !loading && !deepLoading && !retryingPoll;

  const showDeepSearchButton =
    status === "static_done" &&
    deepSearch?.available &&
    !deepLoading &&
    !loading &&
    !retryingPoll;

  const visibleResults =
    results?.filter((result) => result.date !== null && result.date !== "") ?? [];

  return (
    <div className="p-8 max-w-5xl mx-auto w-full flex flex-col items-center text-center">
      <h1 className="text-3xl font-bold mb-4">Identificador de Artistas</h1>
      <form
        onSubmit={handleSearch}
        className="flex w-full flex-col gap-3"
        autoComplete="off"
      >
        <div className="flex w-full gap-2">
          <input
            type="url"
            placeholder="https://..."
            value={imageUrl}
            onChange={(e) => setImageUrl(e.target.value)}
            className="flex-1 min-w-0 border px-3 py-2 rounded"
            autoComplete="off"
            required
          />
          <button
            type="submit"
            disabled={!imageUrl.trim() || loading || deepLoading || retryingPoll}
            className="shrink-0 px-4 py-2 rounded bg-neutral-900 text-white dark:bg-neutral-100 dark:text-neutral-900 disabled:opacity-50"
          >
            {loading ? "Buscando..." : "Buscar"}
          </button>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-neutral-600 dark:text-neutral-400">
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={safeSearchEnabled}
              onChange={(e) => setSafeSearchEnabled(e.target.checked)}
              disabled={loading || deepLoading || retryingPoll}
              className="rounded border-neutral-300 dark:border-neutral-600"
            />
            SafeSearch (filtrar contenido explícito en Google Lens)
          </label>
          <label className="flex items-center gap-2 select-none">
            <span>Tiempo máximo de espera</span>
            <select
              value={pollTimeoutSeconds}
              onChange={(e) =>
                setPollTimeoutSeconds(Number.parseInt(e.target.value, 10))
              }
              disabled={loading || deepLoading || retryingPoll}
              className="rounded border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 px-2 py-1 text-sm"
            >
              {POLL_TIMEOUT_OPTIONS.map((option) => (
                <option key={option.seconds} value={option.seconds}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </form>
      {searchId && (
        <p className="mt-2 text-sm text-neutral-500">Busqueda ID: {searchId}</p>
      )}
      {searchedImageUrl && (
        <section className="mt-4 w-full flex flex-col items-center">
          <h2 className="text-sm font-medium text-neutral-600 dark:text-neutral-400 mb-2">
            Imagen buscada
          </h2>
          <div className="overflow-hidden rounded-lg border border-neutral-200 dark:border-neutral-700 bg-neutral-100 dark:bg-neutral-800">
            {!queryImageError ? (
              // biome-ignore lint/performance/noImgElement: user-provided external image URL
              <img
                src={searchedImageUrl}
                alt="Imagen buscada"
                width={240}
                height={240}
                className="max-w-[240px] max-h-[240px] w-auto h-auto object-contain"
                onError={() => setQueryImageError(true)}
              />
            ) : (
              <div className="w-[240px] h-[240px] flex items-center justify-center px-4 text-center text-sm text-neutral-500 dark:text-neutral-400">
                No se pudo cargar la imagen
              </div>
            )}
          </div>
        </section>
      )}
      {showProgress && (
        <div className="w-full">
          <SearchProgressBar
            progress={progress}
            phase={progressPhase}
            secondsRemaining={pollSecondsRemaining}
            onStop={handleStopPoll}
          />
        </div>
      )}
      {error && <p className="mt-2 text-red-600">{error}</p>}
      {showRetryPollButton && (
        <button
          type="button"
          onClick={handleRetryPoll}
          className="mt-3 px-4 py-2 rounded border border-neutral-300 dark:border-neutral-600 hover:bg-neutral-50 dark:hover:bg-neutral-900 transition-colors text-sm"
        >
          Consultar resultados de nuevo
        </button>
      )}
      {status === "partial" && !error && (
        <p className="mt-2 text-amber-700 dark:text-amber-400">
          {pollStoppedByUser
            ? "Espera detenida. Se muestran los resultados obtenidos hasta el momento."
            : "Tiempo de espera agotado. Se muestran los resultados obtenidos hasta el momento."}
        </p>
      )}
      {showDeepSearchButton && (
        <section className="mt-6 w-full max-w-xl flex flex-col items-center gap-3">
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            Análisis inicial completado
            {deepSearch.pending_urls > 0
              ? ` · ${deepSearch.pending_urls} publicacion${deepSearch.pending_urls !== 1 ? "es" : ""} pueden mejorarse`
              : ""}
            .
          </p>
          <button
            type="button"
            onClick={handleDeepSearch}
            className="px-5 py-2.5 rounded border border-neutral-300 dark:border-neutral-600 hover:bg-neutral-50 dark:hover:bg-neutral-900 transition-colors"
          >
            Búsqueda profunda
          </button>
          <p className="text-xs text-neutral-500 dark:text-neutral-400">
            Puede encontrar fechas faltantes o mejorar fechas poco fiables. Tarda
            más que el análisis inicial.
          </p>
        </section>
      )}
      {showResults && visibleResults.length === 0 && (
        <p className="mt-4 text-neutral-600 dark:text-neutral-400">
          No se encontraron coincidencias con fecha.
        </p>
      )}
      {showResults && visibleResults.length > 0 && (
        <section className="mt-6 w-full">
          <h2 className="text-lg font-semibold mb-4">
            {visibleResults.length} resultado{visibleResults.length !== 1 ? "s" : ""}
            {status === "partial" ? " (parciales)" : ""}
            {status === "static_done" ? " (análisis inicial)" : ""}
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {visibleResults.map((result) => (
              <ResultCard key={result.url} result={result} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
