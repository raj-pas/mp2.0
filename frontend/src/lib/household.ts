import { useQuery } from "@tanstack/react-query";

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

export type LinkRecommendation = {
  link_external_id: string;
  goal_external_id: string;
  account_external_id: string;
  allocated_amount: number;
  frontier_percentile: number | null;
  expected_return: number | null;
  volatility: number | null;
  allocations: { fund_id: string; weight: number }[];
  current_comparison: Record<string, unknown> | null;
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
  link_recommendation_rows?: LinkRecommendation[];
  output?: Record<string, unknown>;
};

export type HouseholdDetail = {
  id: string;
  display_name: string;
  household_type: string;
  household_risk_score: number | null;
  goal_count: number;
  total_assets: number;
  external_assets: number;
  notes: string;
  members: Member[];
  goals: Goal[];
  accounts: Account[];
  latest_portfolio_run: PortfolioRun | null;
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

export function findLinkRecommendation(
  household: HouseholdDetail | undefined,
  goalId: string,
  accountId: string,
): LinkRecommendation | null {
  const run = household?.latest_portfolio_run;
  if (!run?.link_recommendation_rows) return null;
  return (
    run.link_recommendation_rows.find(
      (link) => link.goal_external_id === goalId && link.account_external_id === accountId,
    ) ?? null
  );
}
