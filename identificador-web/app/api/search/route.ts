import { proxyToBackend } from "@/lib/backendFetch";
import { clientImageUrlRejectionMessage } from "@/lib/imageUrl";

export async function POST(req: Request) {
  const body = await req.json().catch(() => null);
  const imageUrl = body?.image_url;
  const safeSearch =
    typeof body?.safe_search === "boolean" ? body.safe_search : true;

  if (typeof imageUrl !== "string" || !imageUrl.trim()) {
    return Response.json(
      { error: "image_url invalida o faltante" },
      { status: 400 },
    );
  }

  const rejectMsg = clientImageUrlRejectionMessage(imageUrl);
  if (rejectMsg) {
    return Response.json({ detail: rejectMsg }, { status: 400 });
  }

  return proxyToBackend(req, "/api/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      image_url: imageUrl.trim(),
      safe_search: safeSearch,
    }),
  });
}
