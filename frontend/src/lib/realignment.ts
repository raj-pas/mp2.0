/**
 * Realignment + HouseholdSnapshot hooks (locked decisions #15 + #37 +
 * canon §6.3a).
 *
 * Wire shapes mirror the R1 endpoints verified live during the
 * pre-R6 smoke (see docs/agent/handoff-log.md 2026-04-30).
 *
 * Vocabulary discipline (canon §6.3a + locked decision #14):
 *   ✅ re-goaling, goal realignment, re-label dollars between goals
 *   ❌ reallocation, transfer, move money
 *
 * The hooks here keep the discipline by NOT exposing any string
 * payloads with retired vocabulary; UI strings flow through `t()` and
 * are scanned by `scripts/check-vocab.sh`.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "./api";
import { householdQueryKey } from "./household";

// --------------------------------------------------------------------
// POST /api/households/{id}/realignment/
// --------------------------------------------------------------------

export type RealignmentPayload = {
  account_goal_amounts: Record<string, Record<string, string>>;
};

export type BigShiftRow = {
  account_id: string;
  account_type: string;
  before_score: number;
  after_score: number;
  delta: number;
};

export type RealignmentResponse = {
  before_snapshot_id: number;
  after_snapshot_id: number;
  big_shifts: BigShiftRow[];
};

export function useRealignment(householdId: string | null) {
  const queryClient = useQueryClient();
  return useMutation<RealignmentResponse, Error, RealignmentPayload>({
    mutationFn: (payload) => {
      if (householdId === null) {
        return Promise.reject(new Error("household id required"));
      }
      return apiFetch<RealignmentResponse>(
        `/api/households/${encodeURIComponent(householdId)}/realignment/`,
        { method: "POST", body: payload },
      );
    },
    onSuccess: () => {
      if (householdId === null) return;
      // Re-goaling mutates GoalAccountLink rows + creates 2 snapshots;
      // invalidate the household detail (KPIs, goal legs) and the
      // snapshots list (history tab).
      queryClient.invalidateQueries({ queryKey: householdQueryKey(householdId) });
      queryClient.invalidateQueries({ queryKey: snapshotsQueryKey(householdId) });
    },
  });
}

// --------------------------------------------------------------------
// HouseholdSnapshot list / detail / restore
// --------------------------------------------------------------------

export type SnapshotTrigger =
  | "realignment"
  | "cash_in"
  | "cash_out"
  | "re_link"
  | "override"
  | "re_goal"
  | "restore";

export type SnapshotSummary = {
  sh_aum: number;
  ext_aum: number;
  total_aum: number;
  goal_count: number;
  account_count: number;
  blended_score: number;
};

export type SnapshotListRow = {
  id: number;
  triggered_by: SnapshotTrigger;
  label: string;
  summary: SnapshotSummary;
  created_at: string;
  created_by: string;
};

export type SnapshotDetail = SnapshotListRow & {
  snapshot: {
    goals: unknown[];
    members: unknown[];
    accounts: unknown[];
    household: Record<string, unknown>;
    external_holdings: unknown[];
  };
};

export const snapshotsQueryKey = (householdId: string) => ["snapshots", householdId] as const;

export const snapshotDetailQueryKey = (householdId: string, snapshotId: number) =>
  ["snapshots", householdId, snapshotId] as const;

export function useSnapshots(householdId: string | null) {
  return useQuery<SnapshotListRow[]>({
    queryKey: householdId ? snapshotsQueryKey(householdId) : ["snapshots", "_none"],
    queryFn: () => {
      if (householdId === null) return Promise.reject(new Error("household id required"));
      return apiFetch<SnapshotListRow[]>(
        `/api/households/${encodeURIComponent(householdId)}/snapshots/`,
      );
    },
    enabled: householdId !== null,
  });
}

export function useSnapshot(householdId: string | null, snapshotId: number | null) {
  return useQuery<SnapshotDetail>({
    queryKey:
      householdId !== null && snapshotId !== null
        ? snapshotDetailQueryKey(householdId, snapshotId)
        : ["snapshots", "_none", "_none"],
    queryFn: () => {
      if (householdId === null || snapshotId === null) {
        return Promise.reject(new Error("household + snapshot id required"));
      }
      return apiFetch<SnapshotDetail>(
        `/api/households/${encodeURIComponent(householdId)}/snapshots/${snapshotId}/`,
      );
    },
    enabled: householdId !== null && snapshotId !== null,
  });
}

export type RestoreResponse = {
  new_snapshot_id: number;
  restored_from_snapshot_id: number;
};

export function useRestoreSnapshot(householdId: string | null) {
  const queryClient = useQueryClient();
  return useMutation<RestoreResponse, Error, { snapshotId: number }>({
    mutationFn: ({ snapshotId }) => {
      if (householdId === null) {
        return Promise.reject(new Error("household id required"));
      }
      return apiFetch<RestoreResponse>(
        `/api/households/${encodeURIComponent(householdId)}/snapshots/${snapshotId}/restore/`,
        { method: "POST" },
      );
    },
    onSuccess: () => {
      if (householdId === null) return;
      queryClient.invalidateQueries({ queryKey: householdQueryKey(householdId) });
      queryClient.invalidateQueries({ queryKey: snapshotsQueryKey(householdId) });
    },
  });
}

// --------------------------------------------------------------------
// /api/preview/blended-account-risk/ — used by RealignModal to flag
// big-shift accounts BEFORE the user clicks Apply (locked decision
// #15 — banner trigger). Note open-question #13: backend threshold
// is `> 5.0` against canon-1-5 weighted score (max ~4), so the banner
// will not actually fire today. Frontend is wired correctly; the
// one-line backend fix is tracked.
// --------------------------------------------------------------------

export type BlendedAccountRiskRequest = {
  household_id: string;
  account_id: string;
  candidate_goal_amounts: Record<string, number>;
};

export type BlendedAccountRiskResponse = {
  before_score: number;
  after_score: number;
  delta: number;
  would_trigger_banner: boolean;
  banner_threshold: number;
};

export function useBlendedAccountRisk(req: BlendedAccountRiskRequest | null) {
  return useQuery<BlendedAccountRiskResponse>({
    queryKey: ["preview", "blended-account-risk", req],
    queryFn: () => {
      if (req === null) return Promise.reject(new Error("blended-account-risk request required"));
      return apiFetch<BlendedAccountRiskResponse>("/api/preview/blended-account-risk/", {
        method: "POST",
        body: req,
      });
    },
    enabled: req !== null,
  });
}
