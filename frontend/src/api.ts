import type {
  EngineOutput,
  ExtractedFact,
  HouseholdDetail,
  HouseholdSummary,
  MatchCandidate,
  ReviewWorkspace,
  ReviewWorkspaceSummary,
  ReviewedClientState,
  SessionPayload,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

let csrfToken = "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(csrfToken && init?.method && init.method !== "GET" ? { "X-CSRFToken": csrfToken } : {}),
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    let message = `Request failed: ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: string };
      message = payload.detail ?? message;
    } catch {
      // Keep the HTTP status message when the response is not JSON.
    }
    throw new Error(message);
  }

  const payload = (await response.json()) as T;
  if (path === "/api/session/" || path === "/api/auth/login/") {
    csrfToken = (payload as SessionPayload).csrf_token ?? csrfToken;
  }
  return payload;
}

export function fetchClients(): Promise<HouseholdSummary[]> {
  return request<HouseholdSummary[]>("/api/clients/");
}

export function fetchClient(id: string): Promise<HouseholdDetail> {
  return request<HouseholdDetail>(`/api/clients/${id}/`);
}

export function generatePortfolio(id: string): Promise<EngineOutput> {
  return request<EngineOutput>(`/api/clients/${id}/generate-portfolio/`, {
    method: "POST",
  });
}

export function fetchSession(): Promise<SessionPayload> {
  return request<SessionPayload>("/api/session/");
}

export function login(email: string, password: string): Promise<SessionPayload> {
  return request<SessionPayload>("/api/auth/login/", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function logout(): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>("/api/auth/logout/", {
    method: "POST",
  });
}

export function fetchReviewWorkspaces(): Promise<ReviewWorkspaceSummary[]> {
  return request<ReviewWorkspaceSummary[]>("/api/review-workspaces/");
}

export function createReviewWorkspace(label: string): Promise<ReviewWorkspace> {
  return request<ReviewWorkspace>("/api/review-workspaces/", {
    method: "POST",
    body: JSON.stringify({ label }),
  });
}

export function fetchReviewWorkspace(id: string): Promise<ReviewWorkspace> {
  return request<ReviewWorkspace>(`/api/review-workspaces/${id}/`);
}

export function uploadReviewDocuments(id: string, files: FileList): Promise<{
  uploaded: Array<{ filename: string; document_id: number }>;
  duplicates: Array<{ filename: string; document_id: number }>;
}> {
  const formData = new FormData();
  Array.from(files).forEach((file) => formData.append("files", file));
  return request<{
    uploaded: Array<{ filename: string; document_id: number }>;
    duplicates: Array<{ filename: string; document_id: number }>;
  }>(`/api/review-workspaces/${id}/upload/`, {
    method: "POST",
    body: formData,
  });
}

export function retryReviewDocument(workspaceId: string, documentId: number): Promise<{
  job_id: number;
  status: string;
}> {
  return request<{ job_id: number; status: string }>(
    `/api/review-workspaces/${workspaceId}/documents/${documentId}/retry/`,
    {
      method: "POST",
    },
  );
}

export function fetchReviewFacts(id: string): Promise<ExtractedFact[]> {
  return request<ExtractedFact[]>(`/api/review-workspaces/${id}/facts/`);
}

export function patchReviewState(
  id: string,
  state: Partial<ReviewedClientState>,
): Promise<{ state: ReviewedClientState; readiness: ReviewedClientState["readiness"] }> {
  return request<{ state: ReviewedClientState; readiness: ReviewedClientState["readiness"] }>(
    `/api/review-workspaces/${id}/state/`,
    {
    method: "PATCH",
    body: JSON.stringify({ state }),
    },
  );
}

export function approveReviewSection(
  id: string,
  section: string,
  status: "approved" | "approved_with_unknowns" | "needs_attention" = "approved",
): Promise<ReviewWorkspace> {
  return request<ReviewWorkspace>(`/api/review-workspaces/${id}/approve-section/`, {
    method: "POST",
    body: JSON.stringify({ section, status }),
  });
}

export function fetchReviewMatches(id: string): Promise<{ candidates: MatchCandidate[] }> {
  return request<{ candidates: MatchCandidate[] }>(`/api/review-workspaces/${id}/matches/`);
}

export function commitReviewWorkspace(
  id: string,
  householdId?: string,
): Promise<{ household_id: string; workspace: ReviewWorkspace }> {
  return request<{ household_id: string; workspace: ReviewWorkspace }>(`/api/review-workspaces/${id}/commit/`, {
    method: "POST",
    body: JSON.stringify(householdId ? { household_id: householdId } : {}),
  });
}
