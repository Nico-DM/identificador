export function formatDate(iso: string | null): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString("es-ES", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function siteInitials(siteName: string): string {
  const cleaned = siteName.replace(/^www\./, "").split(".")[0] ?? siteName;
  return cleaned.slice(0, 2).toUpperCase();
}
