const backendApiUrl = process.env.BACKEND_API_URL ?? "http://localhost:8000";

export async function POST(req: Request) {
  const body = await req.json().catch(() => null);
  const imageUrl = body?.image_url;

  if (typeof imageUrl !== "string" || !imageUrl.trim()) {
    return Response.json({ error: "image_url invalida o faltante" }, { status: 400 });
  }

  try {
    const res = await fetch(`${backendApiUrl}/api/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image_url: imageUrl.trim() }),
    });

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
