import { afterEach, describe, expect, it, vi } from "vitest";
import { proxyToBackend } from "./backendFetch";

describe("proxyToBackend", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("forwards backend JSON response", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify({ status: "ok" }), { status: 200 }),
        ),
    );

    const req = new Request("http://localhost:3000/api/search", {
      headers: { "x-forwarded-for": "1.2.3.4" },
    });
    const res = await proxyToBackend(req, "/api/search", { method: "POST" });
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body).toEqual({ status: "ok" });
    expect(res.headers.get("X-Request-ID")).toBeTruthy();
  });

  it("returns 502 on invalid JSON from backend", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("not json", { status: 200 })),
    );

    const req = new Request("http://localhost:3000/api/search");
    const res = await proxyToBackend(req, "/api/search");
    const body = await res.json();

    expect(res.status).toBe(502);
    expect(body.code).toBe("INVALID_BACKEND_RESPONSE");
  });

  it("returns 502 on network failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("connection refused")),
    );

    const req = new Request("http://localhost:3000/api/search");
    const res = await proxyToBackend(req, "/api/search");
    const body = await res.json();

    expect(res.status).toBe(502);
    expect(body.code).toBe("BACKEND_UNREACHABLE");
  });
});
