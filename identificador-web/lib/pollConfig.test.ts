import { describe, expect, it } from "vitest";
import {
  formatPollDuration,
  POLL_DELAY_MS,
  pollAttemptsForTimeout,
} from "./pollConfig";

describe("pollAttemptsForTimeout", () => {
  it("computes attempts from timeout and delay", () => {
    const attempts = pollAttemptsForTimeout(120);
    expect(attempts).toBe(Math.max(1, Math.ceil((120 * 1000) / POLL_DELAY_MS)));
  });

  it("returns at least 1 attempt", () => {
    expect(pollAttemptsForTimeout(0)).toBe(1);
  });
});

describe("formatPollDuration", () => {
  it("formats seconds only", () => {
    expect(formatPollDuration(30)).toBe("30 s");
  });

  it("formats minutes only", () => {
    expect(formatPollDuration(120)).toBe("2 min");
  });

  it("formats minutes and seconds", () => {
    expect(formatPollDuration(150)).toBe("2 min 30 s");
  });

  it("clamps negative to 0 s", () => {
    expect(formatPollDuration(-10)).toBe("0 s");
  });
});
