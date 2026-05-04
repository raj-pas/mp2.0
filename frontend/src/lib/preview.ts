/**
 * R1 preview-endpoint hooks for the v36 advisor surfaces.
 *
 * Every hook routes through `apiFetch` so CSRF + same-origin cookies
 * flow correctly through Vite's proxy. Wire shapes mirror the R1
 * serializers verified live during the 2026-04-30 deeper smoke
 * (canonical contracts captured in docs/agent/handoff-log.md).
 *
 * Per locked decision #6 the API surface returns canon 1-5 +
 * descriptor + flags; Goal_50 / T / C / 0-100 numbers are NEVER
 * surfaced. The risk-profile endpoint exposes T/C as advisor-
 * transparent intermediates (in 0-100 scale) for the methodology
 * overlay; the goal-score endpoint stays canon-only.
 *
 * Per locked decision #18: `useDebouncedValue` upstream of the query
 * key keeps slider drag / input churn under the 250ms latency budget.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "./api";

// --------------------------------------------------------------------
// Risk profile (Q1-Q4 → T/C/anchor + canon descriptor)
// --------------------------------------------------------------------

export type RiskProfileRequest = {
  q1: number;
  q2: "A" | "B" | "C" | "D";
  q3: string[];
  q4: "A" | "B" | "C" | "D";
};

export type RiskProfileResponse = {
  tolerance_score: number;
  capacity_score: number;
  tolerance_descriptor: string;
  capacity_descriptor: string;
  household_descriptor: string;
  score_1_5: 1 | 2 | 3 | 4 | 5;
  anchor: number;
  flags: string[];
};

export function useRiskProfilePreview(req: RiskProfileRequest | null) {
  return useQuery<RiskProfileResponse>({
    queryKey: ["preview", "risk-profile", req],
    queryFn: () => {
      if (req === null) return Promise.reject(new Error("risk-profile request required"));
      return apiFetch<RiskProfileResponse>("/api/preview/risk-profile/", {
        method: "POST",
        body: req,
      });
    },
    enabled: req !== null,
  });
}

// --------------------------------------------------------------------
// Goal score (anchor + tier + size → canon 1-5 + derivation)
// --------------------------------------------------------------------

export type GoalScoreOverridePayload = {
  score_1_5: 1 | 2 | 3 | 4 | 5;
  descriptor: string;
  rationale: string;
};

export type GoalScoreRequest = {
  anchor: number;
  necessity_score?: number | null;
  goal_amount: number;
  household_aum: number;
  horizon_years: number;
  override?: GoalScoreOverridePayload | null;
};

export type GoalScoreResponse = {
  score_1_5: 1 | 2 | 3 | 4 | 5;
  descriptor: string;
  system_descriptor: string;
  horizon_cap_descriptor: string;
  uncapped_descriptor: string;
  is_horizon_cap_binding: boolean;
  is_overridden: boolean;
  derivation: {
    anchor: number;
    imp_shift: number;
    size_shift: number;
  };
};

export function useGoalScorePreview(req: GoalScoreRequest | null) {
  return useQuery<GoalScoreResponse>({
    queryKey: ["preview", "goal-score", req],
    queryFn: () => {
      if (req === null) return Promise.reject(new Error("goal-score request required"));
      return apiFetch<GoalScoreResponse>("/api/preview/goal-score/", {
        method: "POST",
        body: req,
      });
    },
    enabled: req !== null,
  });
}

// --------------------------------------------------------------------
// Sleeve mix (canon score → fund-level pct mix)
// --------------------------------------------------------------------

export type SleeveMixResponse = {
  score_1_5: 1 | 2 | 3 | 4 | 5;
  reference_score: number;
  mix: Record<string, number>;
  fund_names: Record<string, string>;
};

export function useSleeveMix(score: 1 | 2 | 3 | 4 | 5 | null) {
  return useQuery<SleeveMixResponse>({
    queryKey: ["preview", "sleeve-mix", score],
    queryFn: () => {
      if (score === null) return Promise.reject(new Error("score required"));
      return apiFetch<SleeveMixResponse>("/api/preview/sleeve-mix/", {
        method: "POST",
        body: { score_1_5: score },
      });
    },
    enabled: score !== null,
  });
}

// --------------------------------------------------------------------
// Projection (lognormal quantiles + tier bands)
// --------------------------------------------------------------------

export type ProjectionMode = "ideal" | "current";
export type Tier = "need" | "want" | "wish" | "unsure";

export type ProjectionRequest = {
  start: number;
  score_1_5: 1 | 2 | 3 | 4 | 5;
  horizon_years: number;
  mode?: ProjectionMode;
  is_external?: boolean;
  tier?: Tier;
};

export type ProjectionResponse = {
  p2_5: number;
  p5: number;
  p10: number;
  p25: number;
  p50: number;
  p75: number;
  p90: number;
  p95: number;
  p97_5: number;
  mean: number;
  mu: number;
  sigma: number;
  tier_low_pct: number;
  tier_high_pct: number;
};

export function useProjection(req: ProjectionRequest | null) {
  return useQuery<ProjectionResponse>({
    queryKey: ["preview", "projection", req],
    queryFn: () => {
      if (req === null) return Promise.reject(new Error("projection request required"));
      return apiFetch<ProjectionResponse>("/api/preview/projection/", {
        method: "POST",
        body: req,
      });
    },
    enabled: req !== null,
  });
}

// --------------------------------------------------------------------
// Projection paths (per-percentile point series for the fan chart)
// --------------------------------------------------------------------

export type ProjectionPathsRequest = {
  start: number;
  score_1_5: 1 | 2 | 3 | 4 | 5;
  horizon_years: number;
  percentiles: number[];
  n_steps?: number;
  mode?: ProjectionMode;
  is_external?: boolean;
};

export type ProjectionPathPoint = { year: number; value: number; percentile: number };
export type ProjectionPath = { percentile: number; points: ProjectionPathPoint[] };
export type ProjectionPathsResponse = { paths: ProjectionPath[] };

export function useProjectionPaths(req: ProjectionPathsRequest | null) {
  return useQuery<ProjectionPathsResponse>({
    queryKey: ["preview", "projection-paths", req],
    queryFn: () => {
      if (req === null) return Promise.reject(new Error("projection-paths request required"));
      return apiFetch<ProjectionPathsResponse>("/api/preview/projection-paths/", {
        method: "POST",
        body: req,
      });
    },
    enabled: req !== null,
  });
}

// --------------------------------------------------------------------
// Probability (P[ value at horizon ≥ target ]) — hover-driven
// --------------------------------------------------------------------

export type ProbabilityRequest = {
  start: number;
  score_1_5: 1 | 2 | 3 | 4 | 5;
  horizon_years: number;
  target: number;
  mode?: ProjectionMode;
  is_external?: boolean;
};

export type ProbabilityResponse = { probability: number };

export function useProbability(req: ProbabilityRequest | null) {
  return useQuery<ProbabilityResponse>({
    queryKey: ["preview", "probability", req],
    queryFn: () => {
      if (req === null) return Promise.reject(new Error("probability request required"));
      return apiFetch<ProbabilityResponse>("/api/preview/probability/", {
        method: "POST",
        body: req,
      });
    },
    enabled: req !== null,
  });
}

// --------------------------------------------------------------------
// Optimizer output (improvement % + effective score for the goal)
// --------------------------------------------------------------------

export type OptimizerOutputResponse = {
  ideal_low: number;
  current_low: number;
  improvement_pct: number;
  effective_score_1_5: 1 | 2 | 3 | 4 | 5;
  effective_descriptor: string;
  p_used: number;
  tier: Tier;
};

export function useOptimizerOutput(householdId: string | null, goalId: string | null) {
  return useQuery<OptimizerOutputResponse>({
    queryKey: ["preview", "optimizer-output", householdId, goalId],
    queryFn: () => {
      if (householdId === null || goalId === null) {
        return Promise.reject(new Error("household_id and goal_id required"));
      }
      return apiFetch<OptimizerOutputResponse>("/api/preview/optimizer-output/", {
        method: "POST",
        body: { household_id: householdId, goal_id: goalId },
      });
    },
    enabled: householdId !== null && goalId !== null,
  });
}

// --------------------------------------------------------------------
// Moves (rebalance buys/sells)
// --------------------------------------------------------------------

export type Move = {
  action: "buy" | "sell";
  fund_id: string;
  fund_name: string;
  amount: number;
};

export type MovesResponse = {
  moves: Move[];
  total_buy?: number;
  total_sell?: number;
};

export function useMoves(householdId: string | null, goalId: string | null) {
  return useQuery<MovesResponse>({
    queryKey: ["preview", "moves", householdId, goalId],
    queryFn: () => {
      if (householdId === null || goalId === null) {
        return Promise.reject(new Error("household_id and goal_id required"));
      }
      return apiFetch<MovesResponse>("/api/preview/moves/", {
        method: "POST",
        body: { household_id: householdId, goal_id: goalId },
      });
    },
    enabled: householdId !== null && goalId !== null,
  });
}

// --------------------------------------------------------------------
// GoalRiskOverride list + create (state-changing; AuditEvent-emitting)
// --------------------------------------------------------------------

export type GoalRiskOverride = {
  id: number;
  score_1_5: 1 | 2 | 3 | 4 | 5;
  descriptor: string;
  rationale: string;
  created_by: string;
  created_at: string;
};

export const overrideHistoryQueryKey = (goalId: string) => ["overrides", goalId] as const;

export function useOverrideHistory(goalId: string | null) {
  return useQuery<GoalRiskOverride[]>({
    queryKey: goalId ? overrideHistoryQueryKey(goalId) : ["overrides", "_none"],
    queryFn: () => {
      if (goalId === null) return Promise.reject(new Error("goal id required"));
      return apiFetch<GoalRiskOverride[]>(`/api/goals/${encodeURIComponent(goalId)}/overrides/`);
    },
    enabled: goalId !== null,
  });
}

export type CreateOverridePayload = {
  score_1_5: 1 | 2 | 3 | 4 | 5;
  descriptor: string;
  rationale: string;
};

export type CreateOverrideResponse = {
  override_id: number;
  goal_id: string;
  score_1_5: number;
  descriptor: string;
  created_at: string;
};

export function useCreateOverride(goalId: string | null) {
  const queryClient = useQueryClient();
  return useMutation<CreateOverrideResponse, Error, CreateOverridePayload>({
    mutationFn: (payload) => {
      if (goalId === null) return Promise.reject(new Error("goal id required"));
      return apiFetch<CreateOverrideResponse>(
        `/api/goals/${encodeURIComponent(goalId)}/override/`,
        { method: "POST", body: payload },
      );
    },
    onSuccess: () => {
      if (goalId === null) return;
      queryClient.invalidateQueries({ queryKey: overrideHistoryQueryKey(goalId) });
      // The household detail surface caches goal_risk_score; invalidate
      // so post-save UI reflects the new score on next paint.
      queryClient.invalidateQueries({ queryKey: ["household"] });
    },
  });
}

// A3.6: Manual generate-portfolio mutation (used by RecommendationBanner +
// HouseholdPortfolioPanel). Auto-trigger fires synchronously on commit/wizard/
// override/realignment per locked decision #74; this mutation is the explicit
// "Regenerate" / "Generate" button. Backend returns the freshly-created OR
// reused PortfolioRun in the response payload (no on_commit race per #74).
import type { PortfolioRun } from "./household";
import { householdQueryKey } from "./household";
import { toastError, toastSuccess } from "./toast";

export function useGeneratePortfolio(householdId: string | null) {
  const queryClient = useQueryClient();
  return useMutation<PortfolioRun, Error>({
    mutationFn: () => {
      if (householdId === null) {
        return Promise.reject(new Error("household id required"));
      }
      return apiFetch<PortfolioRun>(
        `/api/clients/${encodeURIComponent(householdId)}/generate-portfolio/`,
        { method: "POST", body: {} },
      );
    },
    onSuccess: () => {
      if (householdId === null) return;
      queryClient.invalidateQueries({ queryKey: householdQueryKey(householdId) });
      toastSuccess("Recommendation refreshed.");
    },
    onError: (err) => {
      toastError("Couldn't refresh recommendation.", { description: err.message });
    },
  });
}
