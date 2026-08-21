/** Debe coincidir con IMAGE_EXTENSIONS en identificador-api/image_validation.py */
export const IMAGE_EXTENSIONS = new Set([
  ".jpg",
  ".jpeg",
  ".png",
  ".gif",
  ".webp",
  ".avif",
  ".bmp",
  ".ico",
  ".heic",
  ".heif",
]);

/**
 * Extensión del último segmento del path, en minúsculas (p. ej. ".png"), o "" si no hay.
 * Devuelve null si la cadena no es una URL http(s) válida.
 */
export function pathImageExtension(urlStr: string): string | null {
  try {
    const u = new URL(urlStr.trim());
    if (u.protocol !== "http:" && u.protocol !== "https:") {
      return null;
    }
    const path = u.pathname || "";
    const segment = path.replace(/\/+$/, "").split("/").pop() ?? "";
    const dot = segment.lastIndexOf(".");
    if (dot === -1) {
      return "";
    }
    return segment.slice(dot).toLowerCase();
  } catch {
    return null;
  }
}

/**
 * Rechazo temprano en cliente: extensión explícita que no es de imagen.
 * null = puede enviarse (sin extensión o extensión de imagen); string = mensaje de error.
 */
export function clientImageUrlRejectionMessage(urlStr: string): string | null {
  const ext = pathImageExtension(urlStr);
  if (ext === null) {
    return "Ingresa una URL http o https válida";
  }
  if (ext === "") {
    return null;
  }
  if (!IMAGE_EXTENSIONS.has(ext)) {
    return "La URL debe ser un enlace directo a imagen (extensión no permitida)";
  }
  return null;
}
