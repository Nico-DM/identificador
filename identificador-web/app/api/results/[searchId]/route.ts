const backendApiUrl = process.env.BACKEND_API_URL ?? "http://localhost:8000";

type RouteContext = {
  params: Promise<{
    searchId: string;
  }>;
};

export async function GET(_req: Request, context: RouteContext) {
  const { searchId } = await context.params;

  try {
    const res = await fetch(`${backendApiUrl}/api/results/${searchId}`);
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
