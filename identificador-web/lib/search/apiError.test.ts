import { describe, expect, it } from "vitest";
import { apiErrorMessage, searchErrorMessage } from "./apiError";

describe("apiErrorMessage", () => {
  it("returns string detail", () => {
    expect(apiErrorMessage({ detail: "Bad request" }, "fallback")).toBe(
      "Bad request",
    );
  });

  it("joins array detail messages", () => {
    expect(
      apiErrorMessage({ detail: [{ msg: "field required" }] }, "fallback"),
    ).toBe("field required");
  });

  it("returns error field", () => {
    expect(apiErrorMessage({ error: "Server error" }, "fallback")).toBe(
      "Server error",
    );
  });

  it("returns fallback when no detail", () => {
    expect(apiErrorMessage({}, "fallback")).toBe("fallback");
  });
});

describe("searchErrorMessage", () => {
  it("returns string error directly", () => {
    expect(searchErrorMessage("timeout", "fallback")).toBe("timeout");
  });

  it("extracts message from Error object", () => {
    expect(searchErrorMessage(new Error("failed"), "fallback")).toBe("failed");
  });

  it("returns fallback for unknown error", () => {
    expect(searchErrorMessage(null, "fallback")).toBe("fallback");
  });
});
