/**
 * Review pipeline hooks (R1 endpoints, locked decisions #4 + #28b
 * + canon §6.7 + §11.4 + §11.8.3).
 *
 * Wire shapes mirror the canonical contracts captured live during the
 * pre-R7 smoke (see docs/agent/handoff-log.md 2026-04-30 — pre-R7).
 *
 * Real-PII discipline (canon §11.8.3):
 *   - Source quotes are minimally redacted server-side
 *     (`web/api/review_redaction.py`)
 *   - Bedrock routing only fires for `data_origin === "real_derived"`
 *   - Workspace timeline serializer's sanitized projection drives
 *     the audit-visible event list
 *
 * Source-priority hierarchy (canon §11.4):
 *   - System-of-record > Structured documents > Note-derived facts
 *   - Cross-class mismatches resolve silently to higher-priority
 *     source — they DON'T appear as conflicts
 *   - Same-class disagreements surface in the conflict review UI
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "./api";

// --------------------------------------------------------------------
// Types — mirror ReviewWorkspaceSerializer + nested rows
// --------------------------------------------------------------------

export type DataOrigin = "real_derived" | "synthetic";

export type WorkspaceStatus = "draft" | "processing" | "review_ready" | "committed" | "archived";

export type DocumentStatus =
  | "uploaded"
  | "classified"
  | "text_extracted"
  | "ocr_required"
  | "facts_extracted"
  | "reconciled"
  | "extracted"
  | "failed"
  | "unsupported"
  | "manual_entry"
  | "skipped";

export type ProcessingJobStatus = "queued" | "processing" | "completed" | "failed";

export type ReviewDocument = {
  id: number;
  original_filename: string;
  content_type: string;
  extension: string;
  file_size: number;
  sha256: string;
  status: DocumentStatus;
  document_type: string | null;
  ocr_overflow: boolean;
  processing_metadata: Record<string, unknown>;
  retry_eligible: boolean;
  failure_code: string | null;
  failure_reason: string | null;
  failure_stage: string | null;
  created_at: string;
  updated_at: string;
};

export type ProcessingJob = {
  id: number;
  document_id: number;
  job_type: string;
  status: ProcessingJobStatus;
  attempts: number;
  max_attempts: number;
  last_error: string;
  metadata: Record<string, unknown>;
  locked_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  is_stale: boolean;
  retry_eligible: boolean;
  created_at: string;
  updated_at: string;
};

export type ReadinessRow = { section: string; label: string };

/**
 * Wire shape note: fresh workspaces (no facts yet) return `readiness:
 * {}` rather than the full object. Optional fields below tolerate that
 * state; consumers should `?? []` / `?? false` defensively.
 */
export type Readiness = {
  engine_ready?: boolean;
  construction_ready?: boolean;
  kyc_compliance_ready?: boolean;
  missing?: ReadinessRow[];
  construction_missing?: ReadinessRow[];
};

export type SectionApprovalStatus =
  | "approved"
  | "approved_with_unknowns"
  | "needs_attention"
  | "not_ready_for_recommendation";

export type SectionApproval = {
  section: string;
  status: SectionApprovalStatus;
  notes: string;
  data: Record<string, unknown>;
  approved_by_email: string;
  approved_at: string;
};

export type WorkerHealth = {
  status: "online" | "stale" | "offline" | "idle";
  name?: string;
  last_seen_at?: string | null;
  active_job_count?: number;
};

export type ReviewWorkspace = {
  id: number;
  external_id: string;
  label: string;
  owner_email: string;
  status: WorkspaceStatus;
  data_origin: DataOrigin;
  linked_household_id: string | null;
  reviewed_state: Record<string, unknown>;
  readiness: Readiness;
  match_candidates: unknown[];
  documents: ReviewDocument[];
  processing_jobs: ProcessingJob[];
  section_approvals: SectionApproval[];
  /**
   * Sections the backend's commit gate requires approved for this
   * workspace. The frontend MUST drive its approval UI off this list
   * — hardcoding it client-side drifts from `ENGINE_REQUIRED_SECTIONS`
   * and silently breaks commit (the frontend either hides required
   * sections or shows non-required ones the user can never satisfy).
   */
  required_sections: string[];
  worker_health: WorkerHealth;
  timeline: Array<{ action: string; created_at: string; metadata: Record<string, unknown> }>;
  created_at: string;
  updated_at: string;
};

export type ReviewWorkspaceListRow = Pick<
  ReviewWorkspace,
  | "id"
  | "external_id"
  | "label"
  | "owner_email"
  | "status"
  | "data_origin"
  | "linked_household_id"
  | "created_at"
  | "updated_at"
> & {
  document_count: number;
};

// --------------------------------------------------------------------
// Query keys
// --------------------------------------------------------------------

export const REVIEW_WORKSPACES_KEY = ["review-workspaces"] as const;
export const reviewWorkspaceKey = (id: string) => ["review-workspace", id] as const;
export const reviewWorkspaceStateKey = (id: string) => ["review-workspace", id, "state"] as const;

// --------------------------------------------------------------------
// List + detail
// --------------------------------------------------------------------

export function useReviewWorkspaces(enabled = true) {
  return useQuery<ReviewWorkspaceListRow[]>({
    queryKey: REVIEW_WORKSPACES_KEY,
    queryFn: () => apiFetch<ReviewWorkspaceListRow[]>("/api/review-workspaces/"),
    enabled,
  });
}

export function useReviewWorkspace(
  workspaceId: string | null,
  options: { polling?: boolean } = {},
) {
  return useQuery<ReviewWorkspace>({
    queryKey: workspaceId ? reviewWorkspaceKey(workspaceId) : ["review-workspace", "_none"],
    queryFn: () => {
      if (workspaceId === null) return Promise.reject(new Error("workspace id required"));
      return apiFetch<ReviewWorkspace>(
        `/api/review-workspaces/${encodeURIComponent(workspaceId)}/`,
      );
    },
    enabled: workspaceId !== null,
    // Live-poll while documents are still processing (locked decision
    // #18 latency budget — 3s polling is well under the worker's
    // typical processing time for synthetic docs).
    refetchInterval: (query) => {
      if (options.polling !== true) return false;
      const data = query.state.data;
      if (data === undefined) return 3000;
      // Backend ProcessingJob.Status is `queued | processing | completed
      // | failed`. Earlier shipped values were `running`/`done`, which
      // never matched and stopped polling the moment the worker
      // claimed a job — leaving the UI frozen at "processing".
      const stillProcessing = data.processing_jobs.some(
        (job) => job.status === "queued" || job.status === "processing",
      );
      if (!stillProcessing) return false;
      // Phase 5b.7: exponential backoff with jitter while still
      // processing. Starts at 3s; doubles up to 30s. fetchFailureCount
      // tracks consecutive errors / no-state-change refetches; we
      // approximate by using dataUpdateCount + errorUpdateCount to
      // back off when the workspace state isn't changing. Reduces
      // polling cost for slow Bedrock-bound real-PII workspaces
      // without losing responsiveness during active work.
      const updates =
        query.state.dataUpdateCount + query.state.errorUpdateCount;
      const baseMs = Math.min(3000 * 2 ** Math.floor(updates / 5), 30000);
      const jitter = Math.floor(Math.random() * 500);
      return baseMs + jitter;
    },
  });
}

// --------------------------------------------------------------------
// Workspace lifecycle mutations
// --------------------------------------------------------------------

export type CreateWorkspacePayload = {
  label: string;
  data_origin?: DataOrigin;
};

export function useCreateWorkspace() {
  const qc = useQueryClient();
  return useMutation<ReviewWorkspace, Error, CreateWorkspacePayload>({
    mutationFn: (payload) =>
      apiFetch<ReviewWorkspace>("/api/review-workspaces/", {
        method: "POST",
        body: payload,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: REVIEW_WORKSPACES_KEY });
    },
  });
}

export type UploadDocumentsResponse = {
  uploaded: { filename: string; document_id: number }[];
  duplicates: { filename: string; document_id: number }[];
  ignored: { filename: string; reason: string }[];
};

export type UploadDocumentsArgs = {
  workspaceId: string;
  files: FileList | File[];
};

/**
 * Workspace id is per-call so the DocDropOverlay can chain
 * `useCreateWorkspace().onSuccess → useUploadDocuments().mutate`
 * without relying on stale hook closures.
 */
export function useUploadDocuments() {
  const qc = useQueryClient();
  return useMutation<UploadDocumentsResponse & { workspaceId: string }, Error, UploadDocumentsArgs>(
    {
      mutationFn: async ({ workspaceId, files }) => {
        const formData = new FormData();
        const list = files instanceof FileList ? Array.from(files) : files;
        for (const file of list) {
          formData.append("files", file);
        }
        const response = await apiFetch<UploadDocumentsResponse>(
          `/api/review-workspaces/${encodeURIComponent(workspaceId)}/upload/`,
          { method: "POST", body: formData },
        );
        return { ...response, workspaceId };
      },
      onSuccess: (data) => {
        qc.invalidateQueries({ queryKey: reviewWorkspaceKey(data.workspaceId) });
        qc.invalidateQueries({ queryKey: REVIEW_WORKSPACES_KEY });
      },
    },
  );
}

// --------------------------------------------------------------------
// Per-doc detail (Phase 5b.5 — DocDetailPanel slide-out)
// --------------------------------------------------------------------

export type ContributedFact = {
  fact_id: number;
  field: string;
  label: string;
  section: string;
  value: unknown;
  confidence: "high" | "medium" | "low";
  derivation_method: "extracted" | "inferred" | "defaulted";
  source_location: string;
  source_page: number | null;
  redacted_evidence_quote: string;
  asserted_at: string | null;
};

export type ReviewDocumentDetail = ReviewDocument & {
  contributed_facts: ContributedFact[];
};

export const reviewDocumentKey = (workspaceId: string, documentId: number) =>
  ["review-workspace", workspaceId, "document", documentId] as const;

export function useReviewDocument(workspaceId: string | null, documentId: number | null) {
  return useQuery<ReviewDocumentDetail>({
    queryKey:
      workspaceId !== null && documentId !== null
        ? reviewDocumentKey(workspaceId, documentId)
        : ["review-workspace", "_none", "document", -1],
    queryFn: () => {
      if (workspaceId === null || documentId === null) {
        return Promise.reject(new Error("workspace+document required"));
      }
      return apiFetch<ReviewDocumentDetail>(
        `/api/review-workspaces/${encodeURIComponent(workspaceId)}/documents/${documentId}/`,
      );
    },
    enabled: workspaceId !== null && documentId !== null,
  });
}

export function useRetryDocument(workspaceId: string | null) {
  const qc = useQueryClient();
  return useMutation<unknown, Error, { documentId: number }>({
    mutationFn: ({ documentId }) => {
      if (workspaceId === null) {
        return Promise.reject(new Error("workspace id required"));
      }
      return apiFetch(
        `/api/review-workspaces/${encodeURIComponent(workspaceId)}/documents/${documentId}/retry/`,
        { method: "POST" },
      );
    },
    onSuccess: () => {
      if (workspaceId === null) return;
      qc.invalidateQueries({ queryKey: reviewWorkspaceKey(workspaceId) });
    },
  });
}

/**
 * Advisor escape hatch: mark a document as manual-entry so the workspace
 * reconcile skips it (no fact contributions) and the advisor can fill
 * the missing fields by hand via the review-screen state editor.
 *
 * Use when extraction can't recover (e.g. failure_code is
 * `bedrock_token_limit` after retries, or `bedrock_non_json` repeatedly).
 * Distinct from retry: retry assumes the next attempt might succeed;
 * manual-entry is a deliberate handoff.
 */
export type ManualEntryResponse = {
  document_id: number;
  status: "manual_entry";
  previous_status: DocumentStatus;
  previous_failure_code: string;
};

export function useMarkManualEntry(workspaceId: string | null) {
  const qc = useQueryClient();
  return useMutation<ManualEntryResponse, Error, { documentId: number }>({
    mutationFn: ({ documentId }) => {
      if (workspaceId === null) {
        return Promise.reject(new Error("workspace id required"));
      }
      return apiFetch<ManualEntryResponse>(
        `/api/review-workspaces/${encodeURIComponent(workspaceId)}/documents/${documentId}/manual-entry/`,
        { method: "POST" },
      );
    },
    onSuccess: () => {
      if (workspaceId === null) return;
      qc.invalidateQueries({ queryKey: reviewWorkspaceKey(workspaceId) });
      qc.invalidateQueries({ queryKey: reviewWorkspaceStateKey(workspaceId) });
    },
  });
}

// --------------------------------------------------------------------
// State (GET + PATCH for advisor edits / conflict resolutions)
// --------------------------------------------------------------------

export type ReviewedStateResponse = {
  state: Record<string, unknown> & { readiness: Readiness };
  readiness: Readiness;
};

export function useReviewedState(workspaceId: string | null) {
  return useQuery<ReviewedStateResponse>({
    queryKey: workspaceId
      ? reviewWorkspaceStateKey(workspaceId)
      : ["review-workspace", "_none", "state"],
    queryFn: () => {
      if (workspaceId === null) return Promise.reject(new Error("workspace id required"));
      return apiFetch<ReviewedStateResponse>(
        `/api/review-workspaces/${encodeURIComponent(workspaceId)}/state/`,
      );
    },
    enabled: workspaceId !== null,
  });
}

export type StatePatchPayload = {
  /** Top-level state sections to merge (people, accounts, goals, ...). */
  state?: Record<string, unknown>;
  reason?: string;
  requires_reason?: boolean;
  source_fact_ids?: number[];
};

export function useStatePatch(workspaceId: string | null) {
  const qc = useQueryClient();
  return useMutation<ReviewedStateResponse, Error, StatePatchPayload>({
    mutationFn: (payload) => {
      if (workspaceId === null) {
        return Promise.reject(new Error("workspace id required"));
      }
      return apiFetch<ReviewedStateResponse>(
        `/api/review-workspaces/${encodeURIComponent(workspaceId)}/state/`,
        { method: "PATCH", body: payload },
      );
    },
    onSuccess: () => {
      if (workspaceId === null) return;
      qc.invalidateQueries({ queryKey: reviewWorkspaceStateKey(workspaceId) });
      qc.invalidateQueries({ queryKey: reviewWorkspaceKey(workspaceId) });
    },
  });
}

// --------------------------------------------------------------------
// Conflict resolution (Phase 5a)
// --------------------------------------------------------------------

export type ConflictCandidate = {
  fact_id: number;
  value: unknown;
  confidence: "high" | "medium" | "low";
  derivation_method: "extracted" | "inferred" | "defaulted";
  source_document_id: number;
  source_document_filename: string;
  source_document_type: string;
  source_location: string;
  source_page: number | null;
  redacted_evidence_quote: string;
  asserted_at: string | null;
};

export type ReviewConflict = {
  field: string;
  label: string;
  section: string;
  values: string[];
  count: number;
  fact_ids: number[];
  resolved: boolean;
  required: boolean;
  same_authority: boolean;
  source_types: string[];
  candidates?: ConflictCandidate[];
  // Populated after resolution
  chosen_fact_id?: number;
  resolution?: unknown;
  rationale?: string;
  evidence_ack?: boolean;
  resolved_at?: string;
  resolved_by?: string;
  // Phase 5b.13: deferral state.
  deferred?: boolean;
  deferred_at?: string | null;
  deferred_by?: string | null;
  deferred_rationale?: string | null;
  re_surfaced_at?: string | null;
};

export type ResolveConflictPayload = {
  field: string;
  chosen_fact_id: number;
  rationale: string;
  evidence_ack: boolean;
};

export type ResolveConflictResponse = {
  state: Record<string, unknown> & { conflicts?: ReviewConflict[] };
  readiness: Readiness;
  invalidated_approvals: string[];
};

// --------------------------------------------------------------------
// FactOverride (Phase 5b.10 inline fact edit + 5b.11 add-missing-fact)
// --------------------------------------------------------------------

export type ApplyFactOverridePayload = {
  field: string;
  value: unknown;
  rationale: string;
  is_added?: boolean;
};

export type ApplyFactOverrideResponse = {
  override_id: number;
  state: Record<string, unknown> & { readiness?: Readiness };
  readiness: Readiness;
  invalidated_approvals: string[];
};

export function useApplyFactOverride(workspaceId: string | null) {
  const qc = useQueryClient();
  return useMutation<ApplyFactOverrideResponse, Error, ApplyFactOverridePayload>({
    mutationFn: (payload) => {
      if (workspaceId === null) {
        return Promise.reject(new Error("workspace id required"));
      }
      return apiFetch<ApplyFactOverrideResponse>(
        `/api/review-workspaces/${encodeURIComponent(workspaceId)}/facts/override/`,
        { method: "POST", body: payload },
      );
    },
    onSuccess: () => {
      if (workspaceId === null) return;
      qc.invalidateQueries({ queryKey: reviewWorkspaceStateKey(workspaceId) });
      qc.invalidateQueries({ queryKey: reviewWorkspaceKey(workspaceId) });
      // Doc-detail panels also need to refresh — invalidate any
      // doc-detail query for this workspace so contributed_facts
      // reflect the override path.
      qc.invalidateQueries({ queryKey: ["review-workspace", workspaceId, "document"] });
    },
  });
}

export function useResolveConflict(workspaceId: string | null) {
  const qc = useQueryClient();
  return useMutation<ResolveConflictResponse, Error, ResolveConflictPayload>({
    mutationFn: (payload) => {
      if (workspaceId === null) {
        return Promise.reject(new Error("workspace id required"));
      }
      return apiFetch<ResolveConflictResponse>(
        `/api/review-workspaces/${encodeURIComponent(workspaceId)}/conflicts/resolve/`,
        { method: "POST", body: payload },
      );
    },
    onSuccess: () => {
      if (workspaceId === null) return;
      qc.invalidateQueries({ queryKey: reviewWorkspaceStateKey(workspaceId) });
      qc.invalidateQueries({ queryKey: reviewWorkspaceKey(workspaceId) });
    },
  });
}

// --------------------------------------------------------------------
// Bulk conflict resolve (Phase 5b.12) + defer (Phase 5b.13)
// --------------------------------------------------------------------

export type BulkResolutionItem = {
  field: string;
  chosen_fact_id: number;
};

export type BulkResolveConflictsPayload = {
  resolutions: BulkResolutionItem[];
  rationale: string;
  evidence_ack: boolean;
};

export type BulkResolveConflictsResponse = ResolveConflictResponse & {
  resolved_count: number;
};

export function useBulkResolveConflicts(workspaceId: string | null) {
  const qc = useQueryClient();
  return useMutation<BulkResolveConflictsResponse, Error, BulkResolveConflictsPayload>({
    mutationFn: (payload) => {
      if (workspaceId === null) {
        return Promise.reject(new Error("workspace id required"));
      }
      return apiFetch<BulkResolveConflictsResponse>(
        `/api/review-workspaces/${encodeURIComponent(workspaceId)}/conflicts/bulk-resolve/`,
        { method: "POST", body: payload },
      );
    },
    onSuccess: () => {
      if (workspaceId === null) return;
      qc.invalidateQueries({ queryKey: reviewWorkspaceStateKey(workspaceId) });
      qc.invalidateQueries({ queryKey: reviewWorkspaceKey(workspaceId) });
    },
  });
}

export type DeferConflictPayload = {
  field: string;
  rationale: string;
};

export function useDeferConflict(workspaceId: string | null) {
  const qc = useQueryClient();
  return useMutation<ResolveConflictResponse, Error, DeferConflictPayload>({
    mutationFn: (payload) => {
      if (workspaceId === null) {
        return Promise.reject(new Error("workspace id required"));
      }
      return apiFetch<ResolveConflictResponse>(
        `/api/review-workspaces/${encodeURIComponent(workspaceId)}/conflicts/defer/`,
        { method: "POST", body: payload },
      );
    },
    onSuccess: () => {
      if (workspaceId === null) return;
      qc.invalidateQueries({ queryKey: reviewWorkspaceStateKey(workspaceId) });
      qc.invalidateQueries({ queryKey: reviewWorkspaceKey(workspaceId) });
    },
  });
}

// --------------------------------------------------------------------
// Section approval + commit (the gates that produce a Household)
// --------------------------------------------------------------------

export type SectionApprovalPayload = {
  section: string;
  status: SectionApprovalStatus;
  notes?: string;
  data?: Record<string, unknown>;
};

export function useApproveSection(workspaceId: string | null) {
  const qc = useQueryClient();
  return useMutation<ReviewWorkspace, Error, SectionApprovalPayload>({
    mutationFn: (payload) => {
      if (workspaceId === null) {
        return Promise.reject(new Error("workspace id required"));
      }
      return apiFetch<ReviewWorkspace>(
        `/api/review-workspaces/${encodeURIComponent(workspaceId)}/approve-section/`,
        { method: "POST", body: payload },
      );
    },
    onSuccess: () => {
      if (workspaceId === null) return;
      qc.invalidateQueries({ queryKey: reviewWorkspaceKey(workspaceId) });
    },
  });
}

export type CommitWorkspacePayload = {
  /** When set, link to an existing household; else create a new one. */
  household_id?: string;
};

export type CommitWorkspaceResponse = {
  household_id: string;
  workspace: ReviewWorkspace;
};

export function useCommitWorkspace(workspaceId: string | null) {
  const qc = useQueryClient();
  return useMutation<CommitWorkspaceResponse, Error, CommitWorkspacePayload>({
    mutationFn: (payload) => {
      if (workspaceId === null) {
        return Promise.reject(new Error("workspace id required"));
      }
      return apiFetch<CommitWorkspaceResponse>(
        `/api/review-workspaces/${encodeURIComponent(workspaceId)}/commit/`,
        { method: "POST", body: payload },
      );
    },
    onSuccess: () => {
      if (workspaceId === null) return;
      qc.invalidateQueries({ queryKey: reviewWorkspaceKey(workspaceId) });
      qc.invalidateQueries({ queryKey: REVIEW_WORKSPACES_KEY });
      // Also invalidate the global clients list so the new household
      // appears in the picker.
      qc.invalidateQueries({ queryKey: ["clients"] });
    },
  });
}
