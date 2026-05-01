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
  /**
   * Structured detail body. Some endpoints (commit, state PATCH) return
   * a JSON body with `code`, `missing_approvals`, etc. — surface it
   * untyped so callers can pull what they need without re-parsing.
   */
  body?: Record<string, unknown>;
};

export function normalizeApiError(
  error: unknown,
  fallback = "Something went wrong.",
): NormalizedApiError {
  if (error instanceof ApiError) {
    const code = bodyCode(error.body);
    const body =
      error.body && typeof error.body === "object" && !Array.isArray(error.body)
        ? (error.body as Record<string, unknown>)
        : undefined;
    return { status: error.status, message: error.message, code, body };
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
