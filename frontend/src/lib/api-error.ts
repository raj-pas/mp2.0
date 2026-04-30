import { ApiError } from "./api";

/**
 * Normalize errors thrown by `apiFetch` for UI consumption.
 *
 * Returns a stable shape `{ status, message, code? }` that panels can
 * key off when deciding between retry, escalation, or auth redirect.
 */
export type NormalizedApiError = {
  status: number;
  message: string;
  code?: string;
};

export function normalizeApiError(
  error: unknown,
  fallback = "Something went wrong.",
): NormalizedApiError {
  if (error instanceof ApiError) {
    const code = bodyCode(error.body);
    return { status: error.status, message: error.message, code };
  }
  if (error instanceof Error) {
    return { status: 0, message: error.message || fallback };
  }
  return { status: 0, message: fallback };
}

function bodyCode(body: unknown): string | undefined {
  if (body && typeof body === "object" && "code" in body) {
    const code = (body as { code?: unknown }).code;
    if (typeof code === "string") return code;
  }
  return undefined;
}

export function isAuthError(err: NormalizedApiError): boolean {
  return err.status === 401 || err.status === 403;
}
