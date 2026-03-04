"use client";
import { useState } from "react";

export default function Home() {
  const [imageUrl, setImageUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<Array<Record<string, unknown>> | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchId, setSearchId] = useState<string | null>(null);

  const pollResults = async (id: string) => {
    const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
    const maxAttempts = 30;
    const delayMs = 2000;

    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      await delay(delayMs);
      const res = await fetch(`/api/results/${id}`);
      const data = await res.json();

      if (!res.ok) {
        setError(data?.detail ?? data?.error ?? "Error consultando resultados");
        setStatus("error");
        return;
      }

      if (data.status === "done") {
        setResults(data.results ?? []);
        setStatus("done");
        return;
      }

      if (data.status === "error") {
        setError(data.error ?? "Error en el procesamiento");
        setStatus("error");
        return;
      }

      setStatus("processing");
    }

    setError("Tiempo de espera agotado. Intenta de nuevo.");
    setStatus("error");
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!imageUrl.trim()) return;

    setLoading(true);
    setResults(null);
    setError(null);
    setStatus("processing");
    setSearchId(null);

    try {
      const res = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_url: imageUrl.trim() }),
      });
      const data = await res.json();

      if (!res.ok) {
        setError(data?.detail ?? data?.error ?? "Error iniciando busqueda");
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
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-4">Identificador de Artistas</h1>
      <form onSubmit={handleSearch} className="flex gap-2 flex-wrap">
        <input
          type="url"
          placeholder="https://..."
          value={imageUrl}
          onChange={(e) => setImageUrl(e.target.value)}
          className="border px-3 py-2 min-w-[320px]"
          required
        />
        <button type="submit" disabled={!imageUrl.trim() || loading}>
          {loading ? "Buscando..." : "Buscar"}
        </button>
      </form>
      {searchId && <p className="mt-2 text-sm">Busqueda ID: {searchId}</p>}
      {status && <p className="mt-2">Estado: {status}</p>}
      {error && <p className="mt-2 text-red-600">{error}</p>}
      {results && <pre className="mt-4">{JSON.stringify(results, null, 2)}</pre>}
    </div>
  );
}
