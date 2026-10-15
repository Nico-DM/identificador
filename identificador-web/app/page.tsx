"use client";

import { SearchProgressBar } from "@/components/search/SearchProgressBar";
import {
  ContinueBatchPrompt,
  IntroSection,
  QueryImagePreview,
  SearchForm,
  SearchResultsSection,
  SiteFooter,
} from "@/components/search/SearchSections";
import { useSearch } from "@/hooks/useSearch";

export default function Home() {
  const search = useSearch();

  return (
    <div className="p-8 max-w-5xl mx-auto w-full flex flex-col items-center text-center">
      <h1 className="text-3xl font-bold mb-4">Identificador de Artistas</h1>
      <SearchForm
        inputMode={search.inputMode}
        imageUrl={search.imageUrl}
        selectedFile={search.selectedFile}
        safeSearchEnabled={search.safeSearchEnabled}
        batchSize={search.batchSize}
        loading={search.loading}
        continuingBatch={search.continuingBatch}
        retryingPoll={search.retryingPoll}
        canSubmit={search.canSubmit}
        onInputModeChange={search.handleInputModeChange}
        onImageUrlChange={search.setImageUrl}
        onFileChange={search.handleFileChange}
        onSafeSearchChange={search.setSafeSearchEnabled}
        onBatchSizeChange={search.setBatchSize}
        onSubmit={search.handleSearch}
      />
      {search.showIntro && <IntroSection />}
      {search.searchId && (
        <p className="mt-2 text-sm text-neutral-500">
          Busqueda ID: {search.searchId}
        </p>
      )}
      {search.searchedImageUrl && (
        <QueryImagePreview
          searchedImageUrl={search.searchedImageUrl}
          queryImageError={search.queryImageError}
          onImageError={() => search.setQueryImageError(true)}
        />
      )}
      {search.showProgress && (
        <div className="w-full">
          <SearchProgressBar
            progress={search.progress}
            phase={search.progressPhase}
          />
        </div>
      )}
      {search.error && <p className="mt-2 text-red-600">{search.error}</p>}
      {search.showRetryPollButton && (
        <button
          type="button"
          onClick={search.handleRetryPoll}
          className="mt-3 px-4 py-2 rounded border border-neutral-300 dark:border-neutral-600 hover:bg-neutral-50 dark:hover:bg-neutral-900 transition-colors text-sm"
        >
          Consultar resultados de nuevo
        </button>
      )}
      {search.status === "partial" && !search.error && (
        <p className="mt-2 text-amber-700 dark:text-amber-400">
          Se muestran los resultados obtenidos hasta el momento.
        </p>
      )}
      {search.showContinueBatchButton && search.batch && (
        <ContinueBatchPrompt
          batch={search.batch}
          onContinue={search.handleContinueBatch}
          loading={search.continuingBatch}
        />
      )}
      {search.showResults && search.results && (
        <SearchResultsSection results={search.results} status={search.status} />
      )}
      <SiteFooter />
    </div>
  );
}
