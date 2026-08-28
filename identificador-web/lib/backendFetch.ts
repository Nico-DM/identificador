const backendApiUrl = process.env.BACKEND_API_URL ?? "http://localhost:8000";

function getClientIp(req: Request): string {
  const forwarded = req.headers.get("x-forwarded-for");
  if (forwarded) {
    return forwarded.split(",")[0]?.trim() || "unknown";
  }
  return req.headers.get("x-real-ip")?.trim() || "unknown";
}

function createRequestId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function logProxyEvent(
  level: "error" | "warn",
  message: string,
  context: Record<string, unknown>,
) {
  const payload = JSON.stringify({
    timestamp: new Date().toISOString(),
    level: level.toUpperCase(),
    logger: "backendFetch",
    message,
    ...context,
  });
  if (level === "error") {
    console.error(payload);
  } else {
    console.warn(payload);
  }
}

export async function proxyToBackend(
  req: Request,
  path: string,
  init: RequestInit = {},
) {
  const clientIp = getClientIp(req);
  const requestId = req.headers.get("x-request-id") ?? createRequestId();
  const headers = new Headers(init.headers);
  if (clientIp !== "unknown") {
    headers.set("X-Forwarded-For", clientIp);
  }
  headers.set("X-Request-ID", requestId);

  try {
    const res = await fetch(`${backendApiUrl}${path}`, { ...init, headers });
    const payload = await res.json().catch(() => null);

    if (!res.ok) {
      logProxyEvent("warn", "Backend returned error response", {
        event: "backend_error",
        request_id: requestId,
        path,
        status: res.status,
      });
    }

    if (payload === null) {
      logProxyEvent("error", "Invalid JSON from backend", {
        event: "backend_invalid_json",
        request_id: requestId,
        path,
        status: res.status,
      });
      return Response.json(
        {
          detail: "Respuesta invalida del backend",
          code: "INVALID_BACKEND_RESPONSE",
        },
        { status: 502, headers: { "X-Request-ID": requestId } },
      );
    }

    return Response.json(payload, {
      status: res.status,
      headers: { "X-Request-ID": requestId },
    });
  } catch (error) {
    logProxyEvent("error", "Failed to connect to backend", {
      event: "backend_unreachable",
      request_id: requestId,
      path,
      error: error instanceof Error ? error.message : String(error),
    });
    return Response.json(
      {
        detail: "No se pudo conectar con el backend FastAPI",
        code: "BACKEND_UNREACHABLE",
      },
      { status: 502, headers: { "X-Request-ID": requestId } },
    );
  }
}
