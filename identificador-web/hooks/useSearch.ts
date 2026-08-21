"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { clientImageFileRejectionMessage } from "@/lib/imageFile";
import { clientImageUrlRejectionMessage } from "@/lib/imageUrl";
import {
  DEFAULT_POLL_TIMEOUT_SECONDS,
  POLL_DELAY_MS,
  pollAttemptsForTimeout,
} from "@/lib/pollConfig";
import { apiErrorMessage } from "@/lib/search/apiError";
import { abortableDelay } from "@/lib/search/poll";
import type {
  DeepSearchInfo,
  InputMode,
  PollOutcome,
  PollTarget,
  ProgressPhase,
  ResultsPayload,
  SearchProgress,
  SearchResult,
} from "@/lib/search/types";

export function useSearch() {
  const [inputMode, setInputMode] = useState<InputMode>("url");
  const [imageUrl, setImageUrl] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [filePreviewUrl, setFilePreviewUrl] = useState<string | null>(null);
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
  const [pollSecondsRemaining, setPollSecondsRemaining] = useState<
    number | null
  >(null);
  const [pollStoppedByUser, setPollStoppedByUser] = useState(false);
  const pollAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      if (filePreviewUrl) {
        URL.revokeObjectURL(filePreviewUrl);
      }
    };
  }, [filePreviewUrl]);

  const handleFileChange = (file: File | null) => {
    if (filePreviewUrl) {
      URL.revokeObjectURL(filePreviewUrl);
    }
    setSelectedFile(file);
    setFilePreviewUrl(file ? URL.createObjectURL(file) : null);
    setError(null);
  };

  const handleInputModeChange = (mode: InputMode) => {
    setInputMode(mode);
    setError(null);
  };

  const clearStaleFormState = useCallback(() => {
    setImageUrl("");
    setLoading(false);
  }, []);

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
  }, [clearStaleFormState]);

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
  ): PollOutcome => {
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
  ): Promise<PollOutcome> => {
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
          return resolveEarlyPoll(
            data,
            lastResults,
            options.untilStatuses,
            true,
          );
        }
        setError(apiErrorMessage(data, "Error consultando resultados"));
        setStatus("error");
        return "error";
      }

      const res = await fetch(`/api/results/${id}`);
      const data: ResultsPayload = await res.json();

      if (!res.ok) {
        setError(apiErrorMessage(data, "Error consultando resultados"));
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
      if (
        finalData.status &&
        options.untilStatuses.includes(finalData.status)
      ) {
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

  const handleSearch = async (e: React.SubmitEvent) => {
    e.preventDefault();

    if (inputMode === "url") {
      if (!imageUrl.trim()) return;
      const clientMsg = clientImageUrlRejectionMessage(imageUrl);
      if (clientMsg) {
        setError(clientMsg);
        setStatus("error");
        return;
      }
    } else {
      if (!selectedFile) return;
      const clientMsg = clientImageFileRejectionMessage(selectedFile);
      if (clientMsg) {
        setError(clientMsg);
        setStatus("error");
        return;
      }
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
    setSearchedImageUrl(inputMode === "url" ? imageUrl.trim() : filePreviewUrl);
    setQueryImageError(false);

    try {
      let res: Response;
      if (inputMode === "url") {
        res = await fetch("/api/search", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            image_url: imageUrl.trim(),
            safe_search: safeSearchEnabled,
          }),
        });
      } else if (selectedFile) {
        const formData = new FormData();
        formData.append("file", selectedFile);
        formData.append("safe_search", safeSearchEnabled ? "true" : "false");
        res = await fetch("/api/search", {
          method: "POST",
          body: formData,
        });
      } else {
        return;
      }
      const data = await res.json();

      if (!res.ok) {
        setError(apiErrorMessage(data, "Error iniciando busqueda"));
        setStatus("error");
        return;
      }

      setSearchId(data.search_id ?? null);
      setStatus(data.status ?? "processing");
      setPollTarget("static");

      if (data.search_id) {
        const terminal =
          data.status === "done" || data.status === "static_done";
        const outcome = terminal
          ? await (async () => {
              const res = await fetch(`/api/results/${data.search_id}`);
              const payload: ResultsPayload = await res.json();
              if (!res.ok) {
                setError(
                  apiErrorMessage(payload, "Error consultando resultados"),
                );
                setStatus("error");
                return "error" as const;
              }
              applyResultsPayload(payload);
              return payload.status === "error"
                ? ("error" as const)
                : ("done" as const);
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
      const res = await fetch(`/api/search/${searchId}/deep`, {
        method: "POST",
      });
      const data = await res.json();

      if (!res.ok) {
        setError(apiErrorMessage(data, "Error iniciando búsqueda profunda"));
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
    (status === "done" || status === "static_done" || status === "partial") &&
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

  const canSubmit =
    inputMode === "url" ? Boolean(imageUrl.trim()) : selectedFile !== null;

  const showIntro = !searchedImageUrl && !showProgress && !showResults;

  return {
    inputMode,
    imageUrl,
    selectedFile,
    searchedImageUrl,
    queryImageError,
    loading,
    deepLoading,
    results,
    status,
    error,
    searchId,
    deepSearch,
    progressPhase,
    progress,
    safeSearchEnabled,
    pollTimeoutSeconds,
    retryingPoll,
    pollSecondsRemaining,
    pollStoppedByUser,
    showResults,
    showProgress,
    showRetryPollButton,
    showDeepSearchButton,
    canSubmit,
    showIntro,
    setImageUrl,
    setQueryImageError,
    setSafeSearchEnabled,
    setPollTimeoutSeconds,
    handleFileChange,
    handleInputModeChange,
    handleStopPoll,
    handleRetryPoll,
    handleSearch,
    handleDeepSearch,
  };
}
