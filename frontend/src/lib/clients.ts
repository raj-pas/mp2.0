import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "./api";
import { householdQueryKey } from "./household";

/**
 * Lightweight household summary served by the existing
 * `ClientListView` (advisor-only). Matches the shape of
 * `HouseholdListSerializer` on the backend.
 */
export type ClientSummary = {
  id: string;
  display_name: string;
  household_type: string;
  household_risk_score: number | null;
  goal_count: number;
  total_assets: number;
};

export const CLIENTS_QUERY_KEY = ["clients"] as const;

export function useClients(enabled = true) {
  return useQuery<ClientSummary[]>({
    queryKey: CLIENTS_QUERY_KEY,
    queryFn: () => apiFetch<ClientSummary[]>("/api/clients/"),
    enabled,
  });
}

/**
 * Plan v20 §A1.36 (P9/P2.3) — household-scoped audit events for the
 * HouseholdContext "Commits" sub-tab (G10 — re-open audit-trail).
 */
export type AuditEventRow = {
  id: number;
  action: string;
  actor: string;
  entity_type: string;
  entity_id: string;
  metadata: Record<string, unknown>;
  created_at: string | null;
};

export type AuditEventListPayload = {
  events: AuditEventRow[];
  total: number;
  page: number;
  page_size: number;
  kind: AuditEventKind;
};

export type AuditEventKind = "commits" | "all";

export const auditEventsQueryKey = (
  householdId: string,
  kind: AuditEventKind,
  page: number,
) => ["audit-events", householdId, kind, page] as const;

export function useAuditEventsForHousehold(
  householdId: string | null,
  kind: AuditEventKind = "commits",
  page = 1,
) {
  return useQuery<AuditEventListPayload>({
    queryKey:
      householdId !== null
        ? auditEventsQueryKey(householdId, kind, page)
        : ["audit-events", "_none", kind, page],
    queryFn: () => {
      if (householdId === null) {
        return Promise.reject(new Error("household id is required"));
      }
      const params = new URLSearchParams({ kind, page: String(page) });
      return apiFetch<AuditEventListPayload>(
        `/api/clients/${encodeURIComponent(householdId)}/audit-events/?${params.toString()}`,
      );
    },
    enabled: householdId !== null,
  });
}

/**
 * Plan v20 §A1.30 — Phase P2.1 + P2.5 mutation hooks for the
 * HouseholdRoute action sub-bar Re-open / Re-reconcile CTAs.
 *
 * Both hooks navigate to the new ReviewWorkspace on success (redirect
 * URL returned in the response body), and invalidate the household
 * detail + audit events queries so the Commits sub-tab + readiness
 * banners refresh in lockstep (§A1.57 — exact-key invalidation).
 */
export type ReopenResponse = {
  workspace: { external_id: string; [key: string]: unknown };
  redirect_url: string;
};

export function useReopenHousehold(householdId: string | null) {
  const queryClient = useQueryClient();
  return useMutation<ReopenResponse, Error, undefined>({
    mutationFn: () => {
      if (householdId === null) {
        return Promise.reject(new Error("household id required"));
      }
      return apiFetch<ReopenResponse>(
        `/api/clients/${encodeURIComponent(householdId)}/reopen/`,
        { method: "POST" },
      );
    },
    onSuccess: () => {
      if (householdId === null) return;
      // Invalidate the household detail (open-workspace gating reads
      // depend on this) + the audit events feed (Commits sub-tab will
      // surface the new review_workspace_reopened event).
      queryClient.invalidateQueries({ queryKey: householdQueryKey(householdId) });
      queryClient.invalidateQueries({ queryKey: ["audit-events", householdId] });
    },
  });
}

export type ReconcileResponse =
  | { noop: true; redirect_url: null }
  | {
      noop: false;
      workspace: { external_id: string; [key: string]: unknown };
      redirect_url: string;
    };

export function useReconcileHousehold(householdId: string | null) {
  const queryClient = useQueryClient();
  return useMutation<ReconcileResponse, Error, undefined>({
    mutationFn: () => {
      if (householdId === null) {
        return Promise.reject(new Error("household id required"));
      }
      return apiFetch<ReconcileResponse>(
        `/api/clients/${encodeURIComponent(householdId)}/reconcile/`,
        { method: "POST" },
      );
    },
    onSuccess: () => {
      if (householdId === null) return;
      queryClient.invalidateQueries({ queryKey: householdQueryKey(householdId) });
      queryClient.invalidateQueries({ queryKey: ["audit-events", householdId] });
    },
  });
}
