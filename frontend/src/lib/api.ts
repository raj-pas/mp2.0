/**
 * Tiny fetch wrapper for the MP2.0 DRF backend.
 *
 * - Same-origin (Vite dev proxies /api/* to Django at port 8000).
 * - Includes session cookies + Django CSRF token on unsafe methods.
 * - Throws ApiError with status + structured body on non-2xx.
 *
 * Per locked decision #2 (server roundtrip on every interaction), every
 * preview/computation call routes through this client.
 */

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS", "TRACE"]);
const CSRF_COOKIE_NAME = "csrftoken";

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.split("; ").find((row) => row.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.slice(name.length + 1)) : null;
}

export class ApiError extends Error {
  readonly status: number;
  readonly body: unknown;

  constructor(status: number, body: unknown, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

export type ApiInit = Omit<RequestInit, "body"> & {
  body?: unknown;
  signal?: AbortSignal;
};

export async function apiFetch<T = unknown>(path: string, init: ApiInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");

  let body: BodyInit | undefined;
  if (init.body !== undefined && init.body !== null) {
    if (init.body instanceof FormData) {
      body = init.body;
    } else {
      headers.set("Content-Type", "application/json");
      body = JSON.stringify(init.body);
    }
  }

  if (!SAFE_METHODS.has(method)) {
    const csrf = readCookie(CSRF_COOKIE_NAME);
    if (csrf) headers.set("X-CSRFToken", csrf);
  }

  const response = await fetch(path, {
    ...init,
    method,
    headers,
    body,
    credentials: "same-origin",
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") ?? "";
  const payload: unknown = contentType.includes("application/json")
    ? await response.json().catch(() => null)
    : await response.text().catch(() => null);

  if (!response.ok) {
    const detail = extractDetail(payload) ?? `Request failed: ${response.status}`;
    throw new ApiError(response.status, payload, detail);
  }

  return payload as T;
}

function extractDetail(payload: unknown): string | null {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return null;
}
