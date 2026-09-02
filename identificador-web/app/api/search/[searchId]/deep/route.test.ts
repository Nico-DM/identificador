import { describe, expect, it, vi } from "vitest";
import { POST } from "./route";

vi.mock("@/lib/backendFetch", () => ({
  proxyToBackend: vi
    .fn()
    .mockResolvedValue(
      Response.json({ search_id: "abc", status: "deep_processing" }),
    ),
}));

import { proxyToBackend } from "@/lib/backendFetch";

describe("POST /api/search/[searchId]/deep", () => {
  it("proxies deep search to backend", async () => {
    const req = new Request("http://localhost:3000/api/search/abc-123/deep", {
      method: "POST",
    });
    const res = await POST(req, {
      params: Promise.resolve({ searchId: "abc-123" }),
    });
    expect(res.status).toBe(200);
    expect(proxyToBackend).toHaveBeenCalledWith(
      req,
      "/api/search/abc-123/deep",
      { method: "POST" },
    );
  });
});
