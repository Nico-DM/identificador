import { afterEach, describe, expect, it, vi } from "vitest";
import { POST } from "./route";

vi.mock("@/lib/backendFetch", () => ({
  proxyToBackend: vi
    .fn()
    .mockResolvedValue(
      Response.json({ search_id: "abc", status: "processing" }),
    ),
}));

import { proxyToBackend } from "@/lib/backendFetch";

describe("POST /api/search", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("rejects missing image_url in JSON body", async () => {
    const req = new Request("http://localhost:3000/api/search", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({}),
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.detail).toContain("image_url");
  });

  it("rejects invalid image URL extension", async () => {
    const req = new Request("http://localhost:3000/api/search", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ image_url: "https://example.com/file.pdf" }),
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
  });

  it("proxies valid JSON search request", async () => {
    const req = new Request("http://localhost:3000/api/search", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        image_url: "https://example.com/photo.jpg",
        safe_search: false,
      }),
    });
    const res = await POST(req);
    expect(res.status).toBe(200);
    expect(proxyToBackend).toHaveBeenCalledWith(
      req,
      "/api/search",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("rejects missing multipart file", async () => {
    const formData = new FormData();
    const req = new Request("http://localhost:3000/api/search", {
      method: "POST",
      body: formData,
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
  });
});
