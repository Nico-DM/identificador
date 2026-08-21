/** Must match UPLOAD_MAX_BYTES / UPLOAD_IMAGE_EXTENSIONS in the API */
export const UPLOAD_MAX_BYTES = 5 * 1024 * 1024;

export const IMAGE_ACCEPT =
  "image/jpeg,image/png,image/gif,image/webp,image/avif,image/bmp,image/x-icon,image/heic,image/heif,.jpg,.jpeg,.png,.gif,.webp,.avif,.bmp,.ico,.heic,.heif";

const ALLOWED_EXTENSIONS = new Set([
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

function fileExtension(name: string): string {
  const base = name.split(/[/\\]/).pop() ?? name;
  const dot = base.lastIndexOf(".");
  if (dot === -1) {
    return "";
  }
  return base.slice(dot).toLowerCase();
}

/**
 * Rechazo temprano en cliente para archivos subidos.
 * null = puede enviarse; string = mensaje de error.
 */
export function clientImageFileRejectionMessage(file: File): string | null {
  if (file.size === 0) {
    return "El archivo está vacío";
  }
  if (file.size > UPLOAD_MAX_BYTES) {
    return "El archivo no puede superar 5 MB";
  }
  const ext = fileExtension(file.name);
  if (!ext) {
    return "El archivo debe tener una extensión de imagen conocida";
  }
  if (!ALLOWED_EXTENSIONS.has(ext)) {
    return "Tipo de archivo no permitido";
  }
  if (file.type && !file.type.startsWith("image/")) {
    return "El archivo debe ser una imagen";
  }
  return null;
}
