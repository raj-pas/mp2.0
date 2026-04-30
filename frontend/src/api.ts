import type {
  CmaAuditEvent,
  CmaFrontier,
  CMASnapshot,
  ExtractedFact,
  HouseholdDetail,
  HouseholdSummary,
  MatchCandidate,
  PortfolioAuditExport,
  PortfolioRun,
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

export function generatePortfolio(id: string): Promise<PortfolioRun> {
  return request<PortfolioRun>(`/api/clients/${id}/generate-portfolio/`, {
    method: "POST",
  });
}

export function declinePortfolioRun(
  householdId: string,
  runId: string,
  reason = "",
): Promise<PortfolioRun> {
  return request<PortfolioRun>(`/api/clients/${householdId}/portfolio-runs/${runId}/decline/`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export function exportPortfolioAudit(
  householdId: string,
  runId: string,
): Promise<PortfolioAuditExport> {
  return request<PortfolioAuditExport>(
    `/api/clients/${householdId}/portfolio-runs/${runId}/audit-export/`,
  );
}

export function fetchCmaSnapshots(): Promise<CMASnapshot[]> {
  return request<CMASnapshot[]>("/api/cma/snapshots/");
}

export function createCmaDraft(copyFromSnapshotId: string): Promise<CMASnapshot> {
  return request<CMASnapshot>("/api/cma/snapshots/", {
    method: "POST",
    body: JSON.stringify({ copy_from_snapshot_id: copyFromSnapshotId }),
  });
}

export function updateCmaSnapshot(
  id: string,
  payload: Partial<CMASnapshot>,
): Promise<CMASnapshot> {
  return request<CMASnapshot>(`/api/cma/snapshots/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function publishCmaSnapshot(id: string, publishNote: string): Promise<CMASnapshot> {
  return request<CMASnapshot>(`/api/cma/snapshots/${id}/publish/`, {
    method: "POST",
    body: JSON.stringify({ publish_note: publishNote }),
  });
}

export function fetchCmaFrontier(id: string): Promise<CmaFrontier> {
  return request<CmaFrontier>(`/api/cma/snapshots/${id}/frontier/`);
}

export function fetchCmaAudit(): Promise<CmaAuditEvent[]> {
  return request<CmaAuditEvent[]>("/api/cma/audit/");
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

export function createReviewWorkspace(
  label: string,
  dataOrigin = "real_derived",
): Promise<ReviewWorkspace> {
  return request<ReviewWorkspace>("/api/review-workspaces/", {
    method: "POST",
    body: JSON.stringify({ label, data_origin: dataOrigin }),
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
  options: { reason?: string; requires_reason?: boolean; source_fact_ids?: number[] } = {},
): Promise<{ state: ReviewedClientState; readiness: ReviewedClientState["readiness"] }> {
  return request<{ state: ReviewedClientState; readiness: ReviewedClientState["readiness"] }>(
    `/api/review-workspaces/${id}/state/`,
    {
    method: "PATCH",
    body: JSON.stringify({ state, ...options }),
    },
  );
}

export function approveReviewSection(
  id: string,
  section: string,
  status:
    | "approved"
    | "approved_with_unknowns"
    | "needs_attention"
    | "not_ready_for_recommendation" = "approved",
  notes = "",
): Promise<ReviewWorkspace> {
  return request<ReviewWorkspace>(`/api/review-workspaces/${id}/approve-section/`, {
    method: "POST",
    body: JSON.stringify({ section, status, notes }),
  });
}

export function manualReconcileReviewWorkspace(id: string): Promise<{ job_id: number; status: string }> {
  return request<{ job_id: number; status: string }>(
    `/api/review-workspaces/${id}/manual-reconcile/`,
    { method: "POST" },
  );
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
