import { describe, expect, it } from "vitest";
import { clientImageUrlRejectionMessage, pathImageExtension } from "./imageUrl";

describe("pathImageExtension", () => {
  it("returns extension for valid image URL", () => {
    expect(pathImageExtension("https://example.com/photo.jpg")).toBe(".jpg");
  });

  it("normalizes uppercase extension", () => {
    expect(pathImageExtension("https://example.com/photo.PNG")).toBe(".png");
  });

  it("handles trailing slash", () => {
    expect(pathImageExtension("https://example.com/photo.webp/")).toBe(".webp");
  });

  it("returns empty string when no extension", () => {
    expect(pathImageExtension("https://example.com/image")).toBe("");
  });

  it("returns null for invalid URL", () => {
    expect(pathImageExtension("not-a-url")).toBeNull();
  });

  it("returns null for non-http scheme", () => {
    expect(pathImageExtension("ftp://example.com/photo.jpg")).toBeNull();
  });
});

describe("clientImageUrlRejectionMessage", () => {
  it("accepts valid image extension", () => {
    expect(
      clientImageUrlRejectionMessage("https://example.com/photo.jpg"),
    ).toBeNull();
  });

  it("accepts URL without extension", () => {
    expect(
      clientImageUrlRejectionMessage("https://example.com/image"),
    ).toBeNull();
  });

  it("rejects invalid URL", () => {
    expect(clientImageUrlRejectionMessage("not-a-url")).toBe(
      "Ingresa una URL http o https válida",
    );
  });

  it("rejects disallowed extension", () => {
    expect(clientImageUrlRejectionMessage("https://example.com/file.pdf")).toBe(
      "La URL debe ser un enlace directo a imagen (extensión no permitida)",
    );
  });
});
