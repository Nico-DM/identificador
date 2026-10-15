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

describe("POST /api/search/[searchId]/continue", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("proxies to backend continue endpoint", async () => {
    const req = new Request(
      "http://localhost:3000/api/search/abc-123/continue",
      { method: "POST" },
    );
    const res = await POST(req, {
      params: Promise.resolve({ searchId: "abc-123" }),
    });
    expect(res.status).toBe(200);
    expect(proxyToBackend).toHaveBeenCalledWith(
      req,
      "/api/search/abc-123/continue",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
