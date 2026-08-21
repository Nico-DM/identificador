type ApiErrorBody = {
  detail?: unknown;
  error?: string;
};

export function apiErrorMessage(data: unknown, fallback: string): string {
  const body = data as ApiErrorBody;
  const detail = body?.detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail
      .map((item: { msg?: string }) => item?.msg)
      .filter(Boolean)
      .join(" ");
  }
  if (typeof body?.error === "string") {
    return body.error;
  }
  return fallback;
}
