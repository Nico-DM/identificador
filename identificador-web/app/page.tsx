"use client";
import { useState } from "react";
import { clientImageUrlRejectionMessage } from "@/lib/imageUrl";

type SearchResult = {
  date: string | null;
  platform: string | null;
  url: string;
  score: number | null;
  source: string;
  thumbnail?: string | null;
  site_name?: string | null;
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

function ResultCard({ result }: { result: SearchResult }) {
  const [imageError, setImageError] = useState(false);
  const siteName = result.site_name ?? result.platform ?? result.url;
  const showThumbnail = result.thumbnail && !imageError;

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
        {result.date && (
          <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
            {formatDate(result.date)}
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
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchId, setSearchId] = useState<string | null>(null);

  const pollResults = async (id: string) => {
    const delay = (ms: number) =>
      new Promise((resolve) => setTimeout(resolve, ms));
    const maxAttempts = 30;
    const delayMs = 2000;
    let lastResults: SearchResult[] = [];

    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      await delay(delayMs);
      const res = await fetch(`/api/results/${id}`);
      const data = await res.json();

      if (!res.ok) {
        setError(data?.detail ?? data?.error ?? "Error consultando resultados");
        setStatus("error");
        return;
      }

      if (Array.isArray(data.results) && data.results.length > 0) {
        lastResults = data.results;
        setResults(data.results);
      }

      if (data.status === "done") {
        setResults(data.results ?? []);
        setStatus("done");
        return;
      }

      if (data.status === "error") {
        if (lastResults.length > 0) {
          setResults(lastResults);
          setStatus("partial");
          setError(
            "Error en el procesamiento. Se muestran los resultados obtenidos hasta el momento.",
          );
        } else {
          setError(data.error ?? "Error en el procesamiento");
          setStatus("error");
        }
        return;
      }

      setStatus("processing");
    }

    const finalRes = await fetch(`/api/results/${id}`);
    const finalData = await finalRes.json();
    if (finalRes.ok) {
      if (finalData.status === "done") {
        setResults(finalData.results ?? []);
        setStatus("done");
        return;
      }
      if (Array.isArray(finalData.results) && finalData.results.length > 0) {
        lastResults = finalData.results;
      }
    }

    if (lastResults.length > 0) {
      setResults(lastResults);
      setStatus("partial");
      setError(null);
      return;
    }

    setError("Tiempo de espera agotado. Intenta de nuevo.");
    setStatus("error");
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
    setResults(null);
    setError(null);
    setStatus("processing");
    setSearchId(null);
    setSearchedImageUrl(imageUrl.trim());
    setQueryImageError(false);

    try {
      const res = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_url: imageUrl.trim() }),
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

      if (data.search_id) {
        await pollResults(data.search_id);
      }
    } catch {
      setError("No se pudo conectar con el backend");
      setStatus("error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <h1 className="text-3xl font-bold mb-4">Identificador de Artistas</h1>
      <form onSubmit={handleSearch} className="flex gap-2 flex-wrap">
        <input
          type="url"
          placeholder="https://..."
          value={imageUrl}
          onChange={(e) => setImageUrl(e.target.value)}
          className="border px-3 py-2 min-w-[320px] rounded"
          required
        />
        <button
          type="submit"
          disabled={!imageUrl.trim() || loading}
          className="px-4 py-2 rounded bg-neutral-900 text-white dark:bg-neutral-100 dark:text-neutral-900 disabled:opacity-50"
        >
          {loading ? "Buscando..." : "Buscar"}
        </button>
      </form>
      {searchId && (
        <p className="mt-2 text-sm text-neutral-500">Busqueda ID: {searchId}</p>
      )}
      {searchedImageUrl && (
        <section className="mt-4">
          <h2 className="text-sm font-medium text-neutral-600 dark:text-neutral-400 mb-2">
            Imagen buscada
          </h2>
          <div className="inline-block overflow-hidden rounded-lg border border-neutral-200 dark:border-neutral-700 bg-neutral-100 dark:bg-neutral-800">
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
      {status && <p className="mt-2">Estado: {status}</p>}
      {error && <p className="mt-2 text-red-600">{error}</p>}
      {status === "partial" && !error && (
        <p className="mt-2 text-amber-700 dark:text-amber-400">
          Tiempo de espera agotado. Se muestran los resultados obtenidos hasta el
          momento.
        </p>
      )}
      {(status === "done" || status === "partial") &&
        results &&
        results.length === 0 && (
          <p className="mt-4 text-neutral-600 dark:text-neutral-400">
            No se encontraron publicaciones con fecha.
          </p>
        )}
      {(status === "done" || status === "partial") &&
        results &&
        results.length > 0 && (
        <section className="mt-6">
          <h2 className="text-lg font-semibold mb-4">
            {results.length} resultado{results.length !== 1 ? "s" : ""}
            {status === "partial" ? " (parciales)" : ""}
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {results.map((result) => (
              <ResultCard key={result.url} result={result} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
