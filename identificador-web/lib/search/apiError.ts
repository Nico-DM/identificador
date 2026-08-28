type ApiErrorBody = {
  detail?: unknown;
  error?: string;
  code?: string;
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

export function searchErrorMessage(error: unknown, fallback: string): string {
  if (typeof error === "string") {
    return error;
  }
  if (error && typeof error === "object" && "message" in error) {
    const message = (error as { message?: unknown }).message;
    if (typeof message === "string") {
      return message;
    }
  }
  return fallback;
}
