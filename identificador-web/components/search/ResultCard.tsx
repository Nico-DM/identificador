"use client";

import { useState } from "react";
import { formatDate, siteInitials } from "@/lib/search/format";
import type { SearchResult } from "@/lib/search/types";

export function ResultCard({ result }: { result: SearchResult }) {
  const [imageError, setImageError] = useState(false);
  const [faviconError, setFaviconError] = useState(false);
  const siteName = result.site_name ?? result.platform ?? result.url;
  const showThumbnail = result.thumbnail && !imageError;
  const showFavicon = result.favicon && !faviconError;
  const confidence =
    result.confidence ?? (result.date ? "confirmed" : "pending");
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
          // biome-ignore lint/performance/noImgElement: thumbnails from external search engines
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
      <div className="px-1 text-left">
        <div className="flex items-start gap-1.5">
          {showFavicon ? (
            // biome-ignore lint/performance/noImgElement: favicons from external search engines
            <img
              src={result.favicon ?? undefined}
              alt=""
              width={16}
              height={16}
              className="mt-0.5 h-4 w-4 shrink-0 rounded-sm object-contain"
              loading="lazy"
              onError={() => setFaviconError(true)}
            />
          ) : null}
          <div className="min-w-0">
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
        </div>
      </div>
    </article>
  );
}
