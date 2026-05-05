import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "./api";

export type Holding = {
  sleeve_id: string;
  sleeve_name: string;
  weight: number;
  market_value: number;
};

export type Account = {
  id: string;
  owner_person_id: string | null;
  type: string;
  regulatory_objective: string | null;
  regulatory_time_horizon: string | null;
  regulatory_risk_rating: string | null;
  current_value: number;
  contribution_room: number | null;
  is_held_at_purpose: boolean;
  missing_holdings_confirmed: boolean;
  cash_state: string;
  holdings: Holding[];
};

export type GoalAccountLink = {
  id: string;
  goal_id: string;
  account_id: string;
  allocated_amount: number;
  allocated_pct: number | null;
};

export type Goal = {
  id: string;
  name: string;
  target_amount: number | null;
  target_date: string | null;
  necessity_score: number | null;
  current_funded_amount: number;
  contribution_plan: number | null;
  goal_risk_score: number | null;
  status: string;
  notes: string;
  account_allocations: GoalAccountLink[];
};

export type Member = {
  id: string;
  name: string;
  dob: string | null;
  marital_status: string | null;
  investment_knowledge: string | null;
  employment: string | null;
  pensions: number | null;
};

// Hand-synchronized with web/api/serializers.py + engine/schemas.py.
// Migration to OpenAPI codegen (api-types.ts) is post-pilot scope —
// HouseholdDetailSerializer + PortfolioRunSerializer lack @extend_schema
// decorators; drf-spectacular cannot infer SerializerMethodField return
// shapes. See scripts/check-openapi-codegen.sh header for the contract.

export type Allocation = {
  sleeve_id: string;
  sleeve_name: string;
  weight: number;
  fund_type: "building_block" | "whole_portfolio";
  asset_class_weights: Record<string, number>;
  geography_weights: Record<string, number>;
};

export type Rollup = {
  id: string;
  name: string;
  allocated_amount: number;
  allocations: Allocation[];
  expected_return: number;
  volatility: number;
};

export type ProjectionPoint = {
  year: number;
  p10: number;
  p50: number;
  p90: number;
  optimized_percentile_value: number;
};

export type CurrentPortfolioComparison = {
  missing_holdings: boolean;
  status: string;
  reason: string;
  expected_return: number | null;
  volatility: number | null;
  allocations: Allocation[];
  deltas: Array<{ sleeve_id: string; sleeve_name: string; weight_delta: number }>;
  holdings_diagnostics: Array<Record<string, unknown>>;
  unmapped_holdings: Array<Record<string, unknown>>;
  warnings: string[];
};

export type LinkRecommendation = {
  link_id: string;
  goal_id: string;
  goal_name: string;
  account_id: string;
  account_type: string;
  allocated_amount: number;
  horizon_years: number;
  goal_risk_score: 1 | 2 | 3 | 4 | 5;
  frontier_percentile: number;
  allocations: Allocation[];
  expected_return: number;
  volatility: number;
  projected_value: number;
  projection: ProjectionPoint[];
  current_comparison: CurrentPortfolioComparison;
  drift_flags: string[];
  warnings: string[];
  explanation: Record<string, unknown>;
  advisor_summary: string;
  technical_trace: Record<string, unknown>;
};

export type FanChartPoint = {
  link_id: string;
  goal_id: string;
  year: number;
  p10: number;
  p50: number;
  p90: number;
};

export type EngineOutput = {
  schema_version: "engine_output.link_first.v2";
  household_id: string;
  link_recommendations: LinkRecommendation[];
  goal_rollups: Rollup[];
  account_rollups: Rollup[];
  household_rollup: Rollup;
  fan_chart: FanChartPoint[];
  audit_trace: Record<string, unknown>;
  advisor_summary: string;
  technical_trace: Record<string, unknown>;
  run_manifest: { run_signature?: string; [k: string]: unknown };
  warnings: string[];
};

// Persisted PortfolioRunLinkRecommendation rows (DB shape; subset of engine LinkRecommendation).
export type PortfolioRunLinkRow = {
  link_external_id: string;
  goal_external_id: string;
  account_external_id: string;
  allocated_amount: number;
  frontier_percentile: number | null;
  expected_return: number | null;
  volatility: number | null;
  allocations: Allocation[];
  current_comparison: CurrentPortfolioComparison | null;
  explanation: string | null;
  warnings: string[];
};

export type PortfolioRun = {
  id: number;
  external_id: string;
  status: string;
  as_of_date: string | null;
  cma_snapshot_id: string;
  engine_version: string;
  advisor_summary: string | null;
  warnings: string[];
  created_at: string;
  run_signature: string;
  output: EngineOutput | null;
  technical_trace: Record<string, unknown> | null;
  link_recommendation_rows?: PortfolioRunLinkRow[];
  events?: Array<{
    event_type: string;
    reason_code: string;
    note: string;
    metadata: Record<string, unknown>;
    created_at: string;
  }>;
};

export type PortfolioGenerationFailure = {
  action: string;
  reason_code: string;
  exception_summary: string;
  occurred_at: string | null;
};

/**
 * Structured advisor-actionable blocker preventing portfolio generation.
 * Mirrors `web/api/types.py::PortfolioGenerationBlocker` (TypedDict).
 *
 * Per plan v20 §A1.27 + Round 14 #3 LOCKED:
 *   The 12 codes cover every branch in
 *   `portfolio_generation_blockers_for_household`, and the 5
 *   ui_actions map to advisor-friendly fix CTAs (Round 9 #11 LOCKED —
 *   no bypass; every blocker has a fix path).
 *
 * Closes G11 UUID-leak: `account_label` carries the canon-vocab
 * humanized form ("Purpose RRSP at Steadyhand ($890K)") built by
 * `account_helpers.advisor_account_label` server-side; raw external_ids
 * never reach the rendered string.
 *
 * `account_value_basis_points` and `account_unallocated_basis_points`
 * are integer basis points (1 bp = 0.0001 = 0.01%); the rendering
 * layer divides by 10000 + formats via `formatCad`.
 */
export type PortfolioGenerationBlocker = {
  code:
    | "purpose_account_unassigned"
    | "purpose_account_unallocated"
    | "purpose_account_zero_value"
    | "purpose_account_pct_not_100"
    | "goal_missing_target_date"
    | "goal_invalid_risk_score"
    | "household_invalid_risk_score"
    | "no_accounts"
    | "no_goals"
    | "unsupported_account_type"
    | "missing_link_amount"
    | "mixed_amount_pct";
  account_id?: string;
  account_label?: string;
  account_value_basis_points?: number;
  account_unallocated_basis_points?: number;
  goal_id?: string;
  goal_label?: string;
  ui_action:
    | "assign_to_goal"
    | "edit_account_value"
    | "set_goal_horizon"
    | "set_household_risk"
    | "open_review_workspace";
};

/**
 * Legacy JSONField list seeded by `load_synthetic_personas` and
 * historical commits. Each row is `{type?, value, description?}`.
 * R1 introduced the canonical `ExternalHolding` model + endpoints,
 * but the household-detail serializer still surfaces the legacy
 * list for backward compatibility. R7 doc-drop will migrate.
 */
export type ExternalAssetRow = {
  type?: string;
  value: number;
  description?: string;
};

export type HouseholdDetail = {
  id: string;
  display_name: string;
  household_type: string;
  household_risk_score: number | null;
  goal_count: number;
  total_assets: number;
  external_assets: ExternalAssetRow[];
  notes: string;
  members: Member[];
  goals: Goal[];
  accounts: Account[];
  latest_portfolio_run: PortfolioRun | null;
  latest_portfolio_failure: PortfolioGenerationFailure | null;
  /**
   * Advisor-actionable list of blockers preventing portfolio generation,
   * OR an empty list if the household is engine-ready. Computed server-
   * side via `portfolio_generation_blockers_for_household` (same function
   * the auto-trigger helper uses to decide whether to raise
   * `ReviewedStateNotConstructionReady`).
   *
   * Surfacing this on the household payload lets the advisor see WHY
   * generation is blocked without having to click Generate first — the
   * typed-skip path is silent per locked #9, so before this field there
   * was no persistent UI signal of unmet readiness.
   */
  readiness_blockers: string[];
  /**
   * Structured TypedDict-shaped blockers per plan v20 §A1.27.
   * ADDITIVE companion to `readiness_blockers` — frontend prefers this
   * field when present (renders structured BlockerBanner with per-
   * blocker fix CTAs) and falls back to humanized strings on older
   * payloads. `null` when no engine output context exists.
   */
  structured_readiness_blockers: PortfolioGenerationBlocker[] | null;
  portfolio_runs: PortfolioRun[];
};

export const householdQueryKey = (id: string) => ["household", id] as const;

export function useHousehold(id: string | null) {
  return useQuery<HouseholdDetail>({
    queryKey: id ? householdQueryKey(id) : ["household", "_none"],
    queryFn: () => {
      if (id === null) {
        return Promise.reject(new Error("household id is required"));
      }
      return apiFetch<HouseholdDetail>(`/api/clients/${encodeURIComponent(id)}/`);
    },
    enabled: id !== null,
  });
}

export function findGoal(household: HouseholdDetail | undefined, goalId: string): Goal | null {
  return household?.goals.find((g) => g.id === goalId) ?? null;
}

export function findAccount(
  household: HouseholdDetail | undefined,
  accountId: string,
): Account | null {
  return household?.accounts.find((a) => a.id === accountId) ?? null;
}

export function householdInternalAum(household: HouseholdDetail): number {
  return household.accounts.reduce((sum, acc) => sum + Number(acc.current_value || 0), 0);
}

export function householdExternalAum(household: HouseholdDetail): number {
  if (!Array.isArray(household.external_assets)) return 0;
  return household.external_assets.reduce(
    (sum, row) => sum + (Number.isFinite(Number(row.value)) ? Number(row.value) : 0),
    0,
  );
}

export function findLinkRecommendationRow(
  household: HouseholdDetail | undefined,
  goalId: string,
  accountId: string,
): PortfolioRunLinkRow | null {
  const run = household?.latest_portfolio_run;
  if (!run?.link_recommendation_rows) return null;
  return (
    run.link_recommendation_rows.find(
      (link) => link.goal_external_id === goalId && link.account_external_id === accountId,
    ) ?? null
  );
}

export function findGoalRollup(
  household: HouseholdDetail | undefined,
  goalId: string,
): Rollup | null {
  const run = household?.latest_portfolio_run;
  if (!run?.output?.goal_rollups) return null;
  return run.output.goal_rollups.find((r) => r.id === goalId) ?? null;
}

export function findHouseholdRollup(household: HouseholdDetail | undefined): Rollup | null {
  return household?.latest_portfolio_run?.output?.household_rollup ?? null;
}

export function findGoalLinkRecommendations(
  household: HouseholdDetail | undefined,
  goalId: string,
): LinkRecommendation[] {
  const run = household?.latest_portfolio_run;
  if (!run?.output?.link_recommendations) return [];
  return run.output.link_recommendations.filter((rec) => rec.goal_id === goalId);
}

// --------------------------------------------------------------------
// P13 — AssignAccountToGoals (plan v20 §A1.28).
// Wire shape mirrors `AssignAccountToGoalsView` in web/api/views.py.
// Uses basis points throughout (1 bp = 0.0001 dollars) so the wire never
// carries floats; all $-math lives in the modal's input layer.
// --------------------------------------------------------------------

export type AssignAccountNewGoalPayload = {
  name: string;
  target_amount_basis_points: number;
  necessity_score: number;
  risk_score: number;
  /** ISO YYYY-MM-DD string. */
  target_date: string;
};

export type AssignAccountAssignment =
  | {
      goal_id: string; // existing external_id
      allocated_amount_basis_points: number;
    }
  | {
      goal_id: "new";
      new_goal: AssignAccountNewGoalPayload;
      allocated_amount_basis_points: number;
    };

export type AssignAccountPayload = {
  rationale: string;
  assignments: AssignAccountAssignment[];
};

export const treemapQueryKeyAny = (id: string) => ["treemap", id] as const;
export const auditEventsQueryKey = (householdId: string) =>
  ["audit_events", householdId] as const;

/**
 * `useAssignAccountToGoals(householdId, accountId)` — POSTs to
 * `/api/clients/<id>/accounts/<aid>/assign-goals/`. On success invalidates
 * (per §A1.57 cache-invalidation contract):
 *   - household detail (refetches HouseholdDetail incl. readiness_blockers
 *     + latest_portfolio_run from auto-trigger side-effect)
 *   - treemap (per-mode, since allocations changed)
 *   - audit_events (Commits sub-tab + audit timeline)
 * Sister contract: `portfolio_run` is NOT invalidated directly — it
 * comes nested under `household` and refetches with it.
 */
export function useAssignAccountToGoals(
  householdId: string | null,
  accountId: string | null,
) {
  const queryClient = useQueryClient();
  return useMutation<HouseholdDetail, Error, AssignAccountPayload>({
    mutationFn: (payload) => {
      if (householdId === null || accountId === null) {
        return Promise.reject(new Error("household + account ids required"));
      }
      return apiFetch<HouseholdDetail>(
        `/api/clients/${encodeURIComponent(householdId)}/accounts/${encodeURIComponent(accountId)}/assign-goals/`,
        { method: "POST", body: payload },
      );
    },
    onSuccess: () => {
      if (householdId === null) return;
      // Sister §A1.57: household → treemap (any mode) → audit_events.
      // We invalidate the wider treemap key prefix so all modes refetch.
      queryClient.invalidateQueries({ queryKey: householdQueryKey(householdId) });
      queryClient.invalidateQueries({ queryKey: treemapQueryKeyAny(householdId) });
      queryClient.invalidateQueries({ queryKey: auditEventsQueryKey(householdId) });
    },
  });
}
