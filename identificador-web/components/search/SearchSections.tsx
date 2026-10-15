"use client";

import { ResultCard } from "@/components/search/ResultCard";
import { IMAGE_ACCEPT } from "@/lib/imageFile";
import { BATCH_SIZE_OPTIONS } from "@/lib/pollConfig";
import type { BatchInfo, InputMode, SearchResult } from "@/lib/search/types";

type SearchFormProps = {
  inputMode: InputMode;
  imageUrl: string;
  selectedFile: File | null;
  safeSearchEnabled: boolean;
  batchSize: number;
  loading: boolean;
  continuingBatch: boolean;
  retryingPoll: boolean;
  canSubmit: boolean;
  onInputModeChange: (mode: InputMode) => void;
  onImageUrlChange: (value: string) => void;
  onFileChange: (file: File | null) => void;
  onSafeSearchChange: (enabled: boolean) => void;
  onBatchSizeChange: (size: number) => void;
  onSubmit: (event: React.SubmitEvent) => void;
};

export function SearchForm({
  inputMode,
  imageUrl,
  selectedFile,
  safeSearchEnabled,
  batchSize,
  loading,
  continuingBatch,
  retryingPoll,
  canSubmit,
  onInputModeChange,
  onImageUrlChange,
  onFileChange,
  onSafeSearchChange,
  onBatchSizeChange,
  onSubmit,
}: SearchFormProps) {
  const busy = loading || continuingBatch || retryingPoll;

  return (
    <form
      onSubmit={onSubmit}
      className="flex w-full flex-col gap-3"
      autoComplete="off"
    >
      <div
        className="flex w-full justify-center gap-1 rounded-lg border border-neutral-200 dark:border-neutral-700 p-1"
        role="tablist"
        aria-label="Modo de entrada"
      >
        <button
          type="button"
          role="tab"
          aria-selected={inputMode === "url"}
          disabled={busy}
          onClick={() => onInputModeChange("url")}
          className={`flex-1 rounded-md px-3 py-1.5 text-sm transition-colors ${
            inputMode === "url"
              ? "bg-neutral-900 text-white dark:bg-neutral-100 dark:text-neutral-900"
              : "text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-800"
          } disabled:opacity-50`}
        >
          URL
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={inputMode === "file"}
          disabled={busy}
          onClick={() => onInputModeChange("file")}
          className={`flex-1 rounded-md px-3 py-1.5 text-sm transition-colors ${
            inputMode === "file"
              ? "bg-neutral-900 text-white dark:bg-neutral-100 dark:text-neutral-900"
              : "text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-800"
          } disabled:opacity-50`}
        >
          Archivo
        </button>
      </div>
      <div className="flex w-full gap-2">
        {inputMode === "url" ? (
          <input
            key="url-input"
            type="url"
            placeholder="https://..."
            value={imageUrl ?? ""}
            onChange={(e) => onImageUrlChange(e.target.value)}
            className="flex-1 min-w-0 border px-3 py-2 rounded"
            autoComplete="off"
            required
          />
        ) : (
          <input
            key="file-input"
            type="file"
            accept={IMAGE_ACCEPT}
            onChange={(e) => onFileChange(e.target.files?.[0] ?? null)}
            className="flex-1 min-w-0 border px-3 py-2 rounded file:mr-3 file:rounded file:border-0 file:bg-neutral-100 file:px-3 file:py-1 file:text-sm dark:file:bg-neutral-800"
            required
          />
        )}
        <button
          type="submit"
          disabled={!canSubmit || busy}
          className="shrink-0 px-4 py-2 rounded bg-neutral-900 text-white dark:bg-neutral-100 dark:text-neutral-900 disabled:opacity-50"
        >
          {loading ? "Buscando..." : "Buscar"}
        </button>
      </div>
      {inputMode === "file" && selectedFile && (
        <p className="text-left text-sm text-neutral-500 dark:text-neutral-400">
          {selectedFile.name} ({Math.round(selectedFile.size / 1024)} KB)
        </p>
      )}
      <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-neutral-600 dark:text-neutral-400">
        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={safeSearchEnabled}
            onChange={(e) => onSafeSearchChange(e.target.checked)}
            disabled={busy}
            className="rounded border-neutral-300 dark:border-neutral-600"
          />
          SafeSearch (filtrar contenido explícito)
        </label>
        <label className="flex items-center gap-2 select-none">
          <span>Resultados a analizar</span>
          <select
            value={batchSize}
            onChange={(e) =>
              onBatchSizeChange(Number.parseInt(e.target.value, 10))
            }
            disabled={busy}
            className="rounded border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 px-2 py-1 text-sm"
          >
            {BATCH_SIZE_OPTIONS.map((option) => (
              <option key={option.size} value={option.size}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>
    </form>
  );
}

export function IntroSection() {
  return (
    <section className="mt-8 w-full max-w-2xl text-left text-sm leading-relaxed text-neutral-600 dark:text-neutral-400">
      <p>
        Esta herramienta ayuda a estimar cuándo se publicó una obra artística
        buscando coincidencias visuales en la web y extrayendo fechas de las
        publicaciones encontradas.
      </p>
      <ol className="mt-4 list-decimal list-inside space-y-2">
        <li>
          Pegá la URL pública de la imagen o subí un archivo desde tu
          dispositivo (máx. 5 MB).
        </li>
        <li>
          Elegí cuántos resultados analizar por lote y presioná{" "}
          <span className="font-medium text-neutral-800 dark:text-neutral-200">
            Buscar
          </span>
          . Los resultados aparecen a medida que se obtienen.
        </li>
        <li>
          Revisá los resultados con fecha; cada tarjeta enlaza a la fuente
          original.
        </li>
        <li>
          Si quedan candidatos, podés analizar el siguiente lote con{" "}
          <span className="font-medium text-neutral-800 dark:text-neutral-200">
            Analizar siguientes
          </span>
          .
        </li>
      </ol>
    </section>
  );
}

export function QueryImagePreview({
  searchedImageUrl,
  queryImageError,
  onImageError,
}: {
  searchedImageUrl: string;
  queryImageError: boolean;
  onImageError: () => void;
}) {
  return (
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
            className="max-w-60 max-h-60 w-auto h-auto object-contain"
            onError={onImageError}
          />
        ) : (
          <div className="w-60 h-60 flex items-center justify-center px-4 text-center text-sm text-neutral-500 dark:text-neutral-400">
            No se pudo cargar la imagen
          </div>
        )}
      </div>
    </section>
  );
}

export function ContinueBatchPrompt({
  batch,
  onContinue,
  loading,
}: {
  batch: BatchInfo;
  onContinue: () => void;
  loading: boolean;
}) {
  const nextCount = Math.min(batch.size, batch.remaining);
  return (
    <section className="mt-6 w-full max-w-xl flex flex-col items-center gap-3">
      <p className="text-sm text-neutral-600 dark:text-neutral-400">
        Lote completado · {batch.processed_candidates} de{" "}
        {batch.total_candidates} candidatos analizados · quedan{"·"}
        {batch.remaining}.
      </p>
      <button
        type="button"
        onClick={onContinue}
        disabled={loading}
        className="px-5 py-2.5 rounded border border-neutral-300 dark:border-neutral-600 hover:bg-neutral-50 dark:hover:bg-neutral-900 transition-colors disabled:opacity-50"
      >
        {loading ? "Analizando..." : `Analizar siguientes ${nextCount}`}
      </button>
    </section>
  );
}

export function SearchResultsSection({
  results,
  status,
}: {
  results: SearchResult[];
  status: string | null;
}) {
  const visibleResults = results.filter(
    (result) => result.date !== null && result.date !== "",
  );

  if (visibleResults.length === 0) {
    return (
      <p className="mt-4 text-neutral-600 dark:text-neutral-400">
        No se encontraron coincidencias con fecha.
      </p>
    );
  }

  return (
    <section className="mt-6 w-full">
      <h2 className="text-lg font-semibold mb-4">
        {visibleResults.length} resultado
        {visibleResults.length !== 1 ? "s" : ""}
        {status === "processing" || status === "deep_processing"
          ? " (en curso)"
          : ""}
        {status === "batch_done" ? " (lote completado)" : ""}
        {status === "partial" ? " (parciales)" : ""}
      </h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        {visibleResults.map((result) => (
          <ResultCard key={result.url} result={result} />
        ))}
      </div>
    </section>
  );
}

export function SiteFooter() {
  return (
    <footer className="mt-12 w-full max-w-2xl border-t border-neutral-200 dark:border-neutral-800 pt-6 text-xs leading-relaxed text-neutral-500 dark:text-neutral-400">
      <p className="font-medium text-neutral-600 dark:text-neutral-300 mb-1">
        Aviso legal
      </p>
      <p>
        Este sitio no es propietario de ninguna de las imágenes mostradas. Las
        miniaturas y vistas previas pertenecen a sus respectivos autores y
        titulares de derechos de autor; se enlazan a las fuentes originales
        únicamente con fines informativos e identificación.
      </p>
      <p className="mt-4 font-medium text-neutral-600 dark:text-neutral-300 mb-1">
        Contacto
      </p>
      <p>
        Para reportar errores o enviar sugerencias:{" "}
        <a
          href="mailto:nicomgaletto@gmail.com"
          className="underline hover:text-neutral-700 dark:hover:text-neutral-200"
        >
          nicomgaletto@gmail.com
        </a>
      </p>
      <p className="mt-4">
        <a
          href="https://github.com/Nico-DM/identificador"
          target="_blank"
          rel="noopener noreferrer"
          className="underline hover:text-neutral-700 dark:hover:text-neutral-200"
        >
          Repositorio en GitHub
        </a>
      </p>
    </footer>
  );
}
