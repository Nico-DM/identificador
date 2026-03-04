const backendApiUrl = process.env.BACKEND_API_URL ?? "http://localhost:8000";

export async function POST(req: Request) {
  const formData = await req.formData();
  const file = formData.get("file");

  if (!(file instanceof File)) {
    return Response.json(
      { error: "Archivo invalido o faltante" },
      { status: 400 },
    );
  }

  const backendFormData = new FormData();
  backendFormData.append("file", file);

  try {
    const res = await fetch(`${backendApiUrl}/api/search`, {
      method: "POST",
      body: backendFormData,
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
