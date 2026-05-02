/**
 * CMA Workbench data layer (R9, analyst-only).
 *
 * TanStack Query hooks for the 6 CMA endpoints + types mirroring the
 * DRF serializers. Per locked decision #26b, no client-side math
 * duplication: every read/mutation routes to the backend.
 *
 * The CMA Workbench is **analyst-only** (canon §11.8 + locked
 * decision #5 — financial-analyst-only surface). RBAC is enforced at
 * the API layer; this module just calls and lets the API decide.
 */

import { useMutation, useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";

import { apiFetch } from "./api";

// ---------------------------------------------------------------------------
// Types — mirror web/api/serializers.py CMASnapshotSerializer family.
// ---------------------------------------------------------------------------

export type CmaSnapshotStatus = "draft" | "active" | "archived";

export interface CmaFundAssumption {
  fund_id: string;
  name: string;
  expected_return: string; // DRF DecimalField → string
  volatility: string;
  optimizer_eligible: boolean;
  is_whole_portfolio: boolean;
  display_order: number;
  aliases: string[];
  asset_class_weights: Record<string, string>;
  geography_weights: Record<string, string>;
  tax_drag: string;
}

export interface CmaCorrelation {
  row_fund_id: string;
  col_fund_id: string;
  correlation: string; // DRF DecimalField → string
}

export interface CmaSnapshot {
  id: number;
  external_id: string;
  name: string;
  version: number;
  status: CmaSnapshotStatus;
  source: string;
  notes: string;
  latest_publish_note: string;
  published_at: string | null;
  created_at: string;
  updated_at: string;
  fund_assumptions: CmaFundAssumption[];
  correlations: CmaCorrelation[];
}

export interface CmaAuditEvent {
  id: number;
  action: string;
  entity_id: string;
  actor: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface CmaFrontierPoint {
  expected_return: number;
  volatility: number;
  weights: number[];
}

export interface CmaFundPoint {
  id: string;
  name: string;
  expected_return: number;
  volatility: number;
  optimizer_eligible: boolean;
  is_whole_portfolio: boolean;
  aliases: string[];
  asset_class_weights: Record<string, number>;
  geography_weights: Record<string, number>;
}

export interface CmaFrontierBounds {
  expected_return_min: number;
  expected_return_max: number;
  volatility_min: number;
  volatility_max: number;
}

export interface CmaFrontierResponse {
  snapshot_id: string;
  funds: CmaFundPoint[];
  fund_points: CmaFundPoint[]; // legacy alias for `funds`
  efficient: CmaFrontierPoint[];
  bounds: CmaFrontierBounds;
  eligible_fund_count: number;
  whole_portfolio_fund_count: number;
}

// ---------------------------------------------------------------------------
// Read hooks
// ---------------------------------------------------------------------------

export function useCmaSnapshots(): UseQueryResult<CmaSnapshot[]> {
  return useQuery({
    queryKey: ["cma", "snapshots"],
    queryFn: () => apiFetch<CmaSnapshot[]>("/api/cma/snapshots/"),
    staleTime: 60_000,
  });
}

export function useCmaSnapshot(externalId: string | null): UseQueryResult<CmaSnapshot> {
  return useQuery({
    queryKey: ["cma", "snapshot", externalId],
    queryFn: () => apiFetch<CmaSnapshot>(`/api/cma/snapshots/${externalId}/`),
    enabled: Boolean(externalId),
    staleTime: 60_000,
  });
}

export function useCmaActiveSnapshot(): UseQueryResult<CmaSnapshot> {
  return useQuery({
    queryKey: ["cma", "active"],
    queryFn: () => apiFetch<CmaSnapshot>("/api/cma/active/"),
    staleTime: 60_000,
  });
}

export function useCmaAuditLog(): UseQueryResult<CmaAuditEvent[]> {
  return useQuery({
    queryKey: ["cma", "audit"],
    queryFn: () => apiFetch<CmaAuditEvent[]>("/api/cma/audit/"),
    staleTime: 30_000,
  });
}

export function useCmaFrontier(externalId: string | null): UseQueryResult<CmaFrontierResponse> {
  return useQuery({
    queryKey: ["cma", "frontier", externalId],
    queryFn: () =>
      apiFetch<CmaFrontierResponse>(`/api/cma/snapshots/${externalId}/frontier/`),
    enabled: Boolean(externalId),
    staleTime: 60_000,
  });
}

// ---------------------------------------------------------------------------
// Mutation hooks
// ---------------------------------------------------------------------------

export interface CmaDraftCreatePayload {
  copy_from_snapshot_id?: string;
  name?: string;
  notes?: string;
}

export function useCreateCmaDraft() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CmaDraftCreatePayload) =>
      apiFetch<CmaSnapshot>("/api/cma/snapshots/", {
        method: "POST",
        body: payload,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cma", "snapshots"] });
    },
  });
}

export interface CmaPatchPayload {
  name?: string;
  notes?: string;
  fund_assumptions?: Array<Partial<CmaFundAssumption> & { fund_id: string }>;
  correlations?: Array<{ row_fund_id: string; col_fund_id: string; correlation: number | string }>;
}

export function usePatchCmaSnapshot(externalId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CmaPatchPayload) => {
      if (!externalId) throw new Error("usePatchCmaSnapshot requires a snapshot id");
      return apiFetch<CmaSnapshot>(`/api/cma/snapshots/${externalId}/`, {
        method: "PATCH",
        body: payload,
      });
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["cma", "snapshots"] });
      qc.invalidateQueries({ queryKey: ["cma", "snapshot", data.external_id] });
      qc.invalidateQueries({ queryKey: ["cma", "frontier", data.external_id] });
    },
  });
}

export function usePublishCmaSnapshot(externalId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { publish_note?: string }) => {
      if (!externalId) throw new Error("usePublishCmaSnapshot requires a snapshot id");
      return apiFetch<CmaSnapshot>(`/api/cma/snapshots/${externalId}/publish/`, {
        method: "POST",
        body: payload,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cma"] });
    },
  });
}
