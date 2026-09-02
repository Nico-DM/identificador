import { describe, expect, it } from "vitest";
import { clientImageFileRejectionMessage } from "./imageFile";

function makeFile(name: string, size: number, type = "image/jpeg"): File {
  const content = new Uint8Array(size);
  return new File([content], name, { type });
}

describe("clientImageFileRejectionMessage", () => {
  it("accepts valid image file", () => {
    const file = makeFile("photo.jpg", 1024);
    expect(clientImageFileRejectionMessage(file)).toBeNull();
  });

  it("rejects empty file", () => {
    const file = makeFile("photo.jpg", 0);
    expect(clientImageFileRejectionMessage(file)).toBe("El archivo está vacío");
  });

  it("rejects file over 5 MB", () => {
    const file = makeFile("photo.jpg", 5 * 1024 * 1024 + 1);
    expect(clientImageFileRejectionMessage(file)).toBe(
      "El archivo no puede superar 5 MB",
    );
  });

  it("rejects missing extension", () => {
    const file = makeFile("photo", 1024);
    expect(clientImageFileRejectionMessage(file)).toBe(
      "El archivo debe tener una extensión de imagen conocida",
    );
  });

  it("rejects disallowed extension", () => {
    const file = makeFile("document.pdf", 1024, "application/pdf");
    expect(clientImageFileRejectionMessage(file)).toBe(
      "Tipo de archivo no permitido",
    );
  });

  it("rejects non-image MIME type", () => {
    const file = makeFile("photo.jpg", 1024, "text/plain");
    expect(clientImageFileRejectionMessage(file)).toBe(
      "El archivo debe ser una imagen",
    );
  });
});
