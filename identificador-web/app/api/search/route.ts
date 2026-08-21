import { proxyToBackend } from "@/lib/backendFetch";
import { clientImageFileRejectionMessage } from "@/lib/imageFile";
import { clientImageUrlRejectionMessage } from "@/lib/imageUrl";

export async function POST(req: Request) {
  const contentType = req.headers.get("content-type") ?? "";

  if (contentType.includes("multipart/form-data")) {
    const formData = await req.formData();
    const file = formData.get("file");

    if (!(file instanceof File) || file.size === 0) {
      return Response.json(
        { detail: "Falta el archivo de imagen" },
        { status: 400 },
      );
    }

    const rejectMsg = clientImageFileRejectionMessage(file);
    if (rejectMsg) {
      return Response.json({ detail: rejectMsg }, { status: 400 });
    }

    const outbound = new FormData();
    outbound.append("file", file);
    const safeSearch = formData.get("safe_search");
    outbound.append(
      "safe_search",
      safeSearch === "false" || safeSearch === "0" ? "false" : "true",
    );

    return proxyToBackend(req, "/api/search", {
      method: "POST",
      body: outbound,
    });
  }

  const body = await req.json().catch(() => null);
  const imageUrl = body?.image_url;
  const safeSearch =
    typeof body?.safe_search === "boolean" ? body.safe_search : true;

  if (typeof imageUrl !== "string" || !imageUrl.trim()) {
    return Response.json(
      { detail: "image_url invalida o faltante" },
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
