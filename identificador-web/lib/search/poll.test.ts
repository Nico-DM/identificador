import { describe, expect, it } from "vitest";
import { abortableDelay } from "./poll";

describe("abortableDelay", () => {
  it("resolves after delay", async () => {
    const start = Date.now();
    await abortableDelay(50);
    expect(Date.now() - start).toBeGreaterThanOrEqual(40);
  });

  it("rejects immediately if already aborted", async () => {
    const controller = new AbortController();
    controller.abort();
    await expect(abortableDelay(100, controller.signal)).rejects.toThrow(
      "Aborted",
    );
  });

  it("rejects when aborted during wait", async () => {
    const controller = new AbortController();
    const promise = abortableDelay(500, controller.signal);
    controller.abort();
    await expect(promise).rejects.toThrow("Aborted");
  });
});
