import { describe, expect, it, vi } from "vitest";
import { GET } from "./route";

vi.mock("@/lib/backendFetch", () => ({
  proxyToBackend: vi
    .fn()
    .mockResolvedValue(
      Response.json({ search_id: "abc", status: "done", results: [] }),
    ),
}));

import { proxyToBackend } from "@/lib/backendFetch";

describe("GET /api/results/[searchId]", () => {
  it("proxies to backend results endpoint", async () => {
    const req = new Request("http://localhost:3000/api/results/abc-123");
    const res = await GET(req, {
      params: Promise.resolve({ searchId: "abc-123" }),
    });
    expect(res.status).toBe(200);
    expect(proxyToBackend).toHaveBeenCalledWith(req, "/api/results/abc-123");
  });
});
