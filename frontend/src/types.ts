export type HouseholdSummary = {
  id: string;
  display_name: string;
  household_type: "single" | "couple";
  household_risk_score: number;
  goal_count: number;
  total_assets: number;
};

export type Person = {
  id: string;
  name: string;
  dob: string;
  marital_status: string;
  investment_knowledge: string;
  employment: Record<string, unknown>;
  pensions: Array<Record<string, unknown>>;
};

export type Holding = {
  sleeve_id: string;
  sleeve_name: string;
  weight: string;
  market_value: string;
};

export type Account = {
  id: string;
  owner_person_id: string | null;
  type: string;
  regulatory_objective: string;
  regulatory_time_horizon: string;
  regulatory_risk_rating: string;
  current_value: string;
  contribution_room: string | null;
  is_held_at_purpose: boolean;
  holdings: Holding[];
};

export type Goal = {
  id: string;
  name: string;
  target_amount: string;
  target_date: string;
  necessity_score: number;
  current_funded_amount: string;
  contribution_plan: Record<string, unknown>;
  goal_risk_score: number;
  status: "on_track" | "watch" | "off_track";
  notes: string;
  account_allocations: Array<{
    goal_id: string;
    account_id: string;
    allocated_amount: string | null;
    allocated_pct: string | null;
  }>;
};

export type HouseholdDetail = HouseholdSummary & {
  external_assets: Array<Record<string, unknown>>;
  notes: string;
  members: Person[];
  goals: Goal[];
  accounts: Account[];
  last_engine_output: EngineOutput | Record<string, never>;
};

export type Allocation = {
  sleeve_id: string;
  sleeve_name: string;
  weight: number;
};

export type GoalBlend = {
  goal_id: string;
  goal_name: string;
  allocations: Allocation[];
  expected_return: number;
  volatility: number;
  risk_rating: "low" | "medium" | "high";
  frontier_percentile: number;
};

export type EngineOutput = {
  household_id: string;
  goal_blends: GoalBlend[];
  household_blend: Allocation[];
  fan_chart: Array<{
    goal_id: string;
    year: number;
    p10: number;
    p50: number;
    p90: number;
  }>;
  account_risk_ratings: Record<string, "low" | "medium" | "high">;
  household_risk_rating: "low" | "medium" | "high";
  narrative_summary: string;
  audit_trace: {
    model_version: string;
    method: string;
  };
};
