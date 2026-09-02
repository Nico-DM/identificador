import { describe, expect, it } from "vitest";
import { formatDate, siteInitials } from "./format";

describe("formatDate", () => {
  it("returns null for null input", () => {
    expect(formatDate(null)).toBeNull();
  });

  it("returns null for invalid date", () => {
    expect(formatDate("not-a-date")).toBeNull();
  });

  it("formats valid ISO date in Spanish locale", () => {
    const result = formatDate("2024-06-15T12:00:00Z");
    expect(result).toBeTruthy();
    expect(result).toContain("2024");
  });
});

describe("siteInitials", () => {
  it("strips www prefix", () => {
    expect(siteInitials("www.example.com")).toBe("EX");
  });

  it("takes first label", () => {
    expect(siteInitials("reddit.com")).toBe("RE");
  });

  it("uppercases two characters", () => {
    expect(siteInitials("YouTube")).toBe("YO");
  });
});
