"use client";

import { useCallback, useEffect, useState } from "react";
import { clientImageFileRejectionMessage } from "@/lib/imageFile";
import { clientImageUrlRejectionMessage } from "@/lib/imageUrl";
import {
  DEFAULT_BATCH_SIZE,
  POLL_DELAY_MS,
  pollAttemptsForTimeout,
  SAFETY_POLL_TIMEOUT_SECONDS,
} from "@/lib/pollConfig";
import { apiErrorMessage, searchErrorMessage } from "@/lib/search/apiError";
import { abortableDelay } from "@/lib/search/poll";
import type {
  BatchInfo,
  InputMode,
  PollOutcome,
  ProgressPhase,
  ResultsPayload,
  SearchProgress,
  SearchResult,
} from "@/lib/search/types";

const BATCH_TERMINAL_STATUSES = ["batch_done", "done", "error"];

export function useSearch() {
  const [inputMode, setInputMode] = useState<InputMode>("url");
  const [imageUrl, setImageUrl] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [filePreviewUrl, setFilePreviewUrl] = useState<string | null>(null);
  const [searchedImageUrl, setSearchedImageUrl] = useState<string | null>(null);
  const [queryImageError, setQueryImageError] = useState(false);
  const [loading, setLoading] = useState(false);
  const [continuingBatch, setContinuingBatch] = useState(false);
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchId, setSearchId] = useState<string | null>(null);
  const [batch, setBatch] = useState<BatchInfo | null>(null);
  const [progressPhase, setProgressPhase] =
    useState<ProgressPhase>("reverse_image");
  const [progress, setProgress] = useState<SearchProgress>({
    processed: 0,
    total: 0,
  });
  const [safeSearchEnabled, setSafeSearchEnabled] = useState(true);
  const [batchSize, setBatchSize] = useState(DEFAULT_BATCH_SIZE);
  const [canRetryPoll, setCanRetryPoll] = useState(false);
  const [retryingPoll, setRetryingPoll] = useState(false);

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
    if (data.batch) {
      setBatch(data.batch);
    }
    if (data.status) {
      setStatus(data.status);
      if (data.status === "deep_processing") {
        setProgressPhase("deep");
      } else if (
        data.status === "processing" &&
        (data.progress?.total ?? 0) > 0
      ) {
        setProgressPhase("static");
      }
    }
  };

  const pollResults = async (id: string): Promise<PollOutcome> => {
    const maxAttempts = pollAttemptsForTimeout(SAFETY_POLL_TIMEOUT_SECONDS);
    const delayMs = POLL_DELAY_MS;
    let lastResults: SearchResult[] = [];

    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      await abortableDelay(delayMs);

      const res = await fetch(`/api/results/${id}`);
      const data: ResultsPayload = await res.json();

      if (!res.ok) {
        setError(apiErrorMessage(data, "Error consultando resultados"));
        setStatus("error");
        return "error";
      }

      applyResultsPayload(data);

      if (Array.isArray(data.results) && data.results.length > 0) {
        lastResults = data.results;
      }

      if (data.status && BATCH_TERMINAL_STATUSES.includes(data.status)) {
        if (data.status === "error") {
          if (lastResults.length > 0) {
            setResults(lastResults);
            setStatus("partial");
            setError(
              "Error en el procesamiento. Se muestran los resultados obtenidos hasta el momento.",
            );
            return "partial";
          }
          setError(searchErrorMessage(data.error, "Error en el procesamiento"));
          setStatus("error");
          return "error";
        }
        return "done";
      }
    }

    const finalRes = await fetch(`/api/results/${id}`);
    const finalData: ResultsPayload = await finalRes.json();
    if (finalRes.ok) {
      applyResultsPayload(finalData);
      if (
        finalData.status &&
        BATCH_TERMINAL_STATUSES.includes(finalData.status) &&
        finalData.status !== "error"
      ) {
        return "done";
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

  const handleRetryPoll = async () => {
    if (!searchId || retryingPoll) return;

    setRetryingPoll(true);
    setCanRetryPoll(false);
    setError(null);

    try {
      const outcome = await pollResults(searchId);
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
    setContinuingBatch(false);
    setResults(null);
    setError(null);
    setStatus("processing");
    setSearchId(null);
    setBatch(null);
    setProgressPhase("reverse_image");
    setProgress({ processed: 0, total: 0 });
    setCanRetryPoll(false);
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
            batch_size: batchSize,
          }),
        });
      } else if (selectedFile) {
        const formData = new FormData();
        formData.append("file", selectedFile);
        formData.append("safe_search", safeSearchEnabled ? "true" : "false");
        formData.append("batch_size", String(batchSize));
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

      if (data.search_id) {
        const terminal = data.status === "done" || data.status === "batch_done";
        const outcome = terminal
          ? await (async () => {
              const resultsRes = await fetch(`/api/results/${data.search_id}`);
              const payload: ResultsPayload = await resultsRes.json();
              if (!resultsRes.ok) {
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
          : await pollResults(data.search_id);
        if (outcome === "timeout" || outcome === "partial") {
          setCanRetryPoll(true);
        }
      }
    } catch {
      setError("No se pudo conectar con el backend");
      setStatus("error");
    } finally {
      setLoading(false);
    }
  };

  const handleContinueBatch = async () => {
    if (!searchId || continuingBatch || loading) return;

    setContinuingBatch(true);
    setError(null);
    setCanRetryPoll(false);
    setStatus("processing");
    setProgressPhase("static");
    setProgress({ processed: 0, total: 0 });

    try {
      const res = await fetch(`/api/search/${searchId}/continue`, {
        method: "POST",
      });
      const data = await res.json();

      if (!res.ok) {
        setError(apiErrorMessage(data, "Error continuando el análisis"));
        setStatus("batch_done");
        return;
      }

      setStatus(data.status ?? "processing");
      const outcome = await pollResults(searchId);
      if (outcome === "timeout" || outcome === "partial") {
        setCanRetryPoll(true);
      }
    } catch {
      setError("No se pudo conectar con el backend");
      setStatus("batch_done");
    } finally {
      setContinuingBatch(false);
    }
  };

  const hasDatedResults =
    Array.isArray(results) &&
    results.some((result) => result.date !== null && result.date !== "");

  const showResults = Boolean(
    results &&
      (status === "done" ||
        status === "batch_done" ||
        status === "partial" ||
        hasDatedResults),
  );

  const showProgress =
    loading ||
    continuingBatch ||
    status === "processing" ||
    status === "deep_processing" ||
    retryingPoll;

  const showRetryPollButton =
    canRetryPoll && searchId && !loading && !continuingBatch && !retryingPoll;

  const showContinueBatchButton =
    status === "batch_done" &&
    Boolean(batch && batch.remaining > 0) &&
    !loading &&
    !continuingBatch &&
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
    continuingBatch,
    results,
    status,
    error,
    searchId,
    batch,
    progressPhase,
    progress,
    safeSearchEnabled,
    batchSize,
    retryingPoll,
    showResults,
    showProgress,
    showRetryPollButton,
    showContinueBatchButton,
    canSubmit,
    showIntro,
    setImageUrl,
    setQueryImageError,
    setSafeSearchEnabled,
    setBatchSize,
    handleFileChange,
    handleInputModeChange,
    handleRetryPoll,
    handleSearch,
    handleContinueBatch,
  };
}
