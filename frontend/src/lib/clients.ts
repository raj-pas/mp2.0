import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "./api";

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
