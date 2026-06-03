const backendApiUrl = process.env.BACKEND_API_URL ?? "http://localhost:8000";

function getClientIp(req: Request): string {
  const forwarded = req.headers.get("x-forwarded-for");
  if (forwarded) {
    return forwarded.split(",")[0]?.trim() || "unknown";
  }
  return req.headers.get("x-real-ip")?.trim() || "unknown";
}

export async function proxyToBackend(
  req: Request,
  path: string,
  init: RequestInit = {},
) {
  const clientIp = getClientIp(req);
  const headers = new Headers(init.headers);
  if (clientIp !== "unknown") {
    headers.set("X-Forwarded-For", clientIp);
  }

  try {
    const res = await fetch(`${backendApiUrl}${path}`, { ...init, headers });
    const payload = await res
      .json()
      .catch(() => ({ error: "Respuesta invalida del backend" }));
    return Response.json(payload, { status: res.status });
  } catch {
    return Response.json(
      { error: "No se pudo conectar con el backend FastAPI" },
      { status: 502 },
    );
  }
}
