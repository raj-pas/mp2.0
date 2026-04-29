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
  missing_holdings_confirmed: boolean;
  holdings: Holding[];
};

export type Goal = {
  id: string;
  name: string;
  target_amount: string | null;
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
  latest_portfolio_run: PortfolioRun | null;
  portfolio_runs: PortfolioRunSummary[];
};

export type Allocation = {
  sleeve_id: string;
  sleeve_name: string;
  weight: number;
};

export type AllocationDelta = {
  sleeve_id: string;
  sleeve_name: string;
  weight_delta: number;
};

export type LinkRecommendation = {
  link_id: string;
  goal_id: string;
  goal_name: string;
  account_id: string;
  account_type: string;
  allocated_amount: number;
  horizon_years: number;
  goal_risk_score: number;
  frontier_percentile: number;
  allocations: Allocation[];
  expected_return: number;
  volatility: number;
  projected_value: number;
  projection: Array<{
    year: number;
    p10: number;
    p50: number;
    p90: number;
    optimized_percentile_value: number;
  }>;
  current_comparison: {
    missing_holdings: boolean;
    expected_return: number | null;
    volatility: number | null;
    allocations: Allocation[];
    deltas: AllocationDelta[];
  };
  drift_flags: string[];
  advisor_summary: string;
  technical_trace: Record<string, unknown>;
};

export type Rollup = {
  id: string;
  name: string;
  allocated_amount: number;
  allocations: Allocation[];
  expected_return: number;
  volatility: number;
};

export type EngineOutput = {
  schema_version: string;
  household_id: string;
  link_recommendations: LinkRecommendation[];
  goal_rollups: Rollup[];
  account_rollups: Rollup[];
  household_rollup: Rollup;
  fan_chart: Array<{
    link_id: string;
    goal_id: string;
    year: number;
    p10: number;
    p50: number;
    p90: number;
  }>;
  advisor_summary: string;
  technical_trace: Record<string, unknown>;
  warnings: string[];
  audit_trace: {
    model_version: string;
    method: string;
    cma_snapshot_id: string;
    cma_version: number;
  };
};

export type PortfolioRunSummary = {
  id: number;
  external_id: string;
  status: "current" | "stale";
  stale_reason: string;
  cma_snapshot_id: string;
  engine_version: string;
  advisor_summary: string;
  input_hash: string;
  output_hash: string;
  generated_by_email: string;
  created_at: string;
};

export type PortfolioRun = PortfolioRunSummary & {
  output: EngineOutput;
  technical_trace: Record<string, unknown>;
  link_recommendation_rows: Array<{
    goal_external_id: string;
    account_external_id: string;
    allocated_amount: string;
    frontier_percentile: number;
    expected_return: string;
    volatility: string;
    allocations: Allocation[];
  }>;
};

export type CMASnapshot = {
  id: number;
  external_id: string;
  name: string;
  version: number;
  status: "draft" | "active" | "archived";
  source: string;
  notes: string;
  published_at: string | null;
  created_at: string;
  updated_at: string;
  fund_assumptions: Array<{
    fund_id: string;
    name: string;
    expected_return: string;
    volatility: string;
    optimizer_eligible: boolean;
    is_whole_portfolio: boolean;
    display_order: number;
    asset_class_weights: Record<string, number>;
    tax_drag: Record<string, number>;
  }>;
  correlations: Array<{
    row_fund_id: string;
    col_fund_id: string;
    correlation: string;
  }>;
};

export type SessionPayload = {
  authenticated: boolean;
  csrf_token: string;
  user: null | {
    email: string;
    name: string;
    role: string;
    team?: string;
    engine_enabled?: boolean;
  };
};

export type Readiness = {
  engine_ready: boolean;
  kyc_compliance_ready: boolean;
  missing: Array<{
    section: string;
    label: string;
  }>;
};

export type ReviewDocument = {
  id: number;
  original_filename: string;
  content_type: string;
  extension: string;
  file_size: number;
  sha256: string;
  document_type: string;
  status: string;
  failure_reason: string;
  failure_code: string;
  failure_stage: string;
  retry_eligible: boolean;
  ocr_overflow: Record<string, unknown>;
  processing_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ProcessingJob = {
  id: number;
  document_id: number | null;
  job_type: string;
  status: string;
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

export type SectionApproval = {
  id: number;
  section: string;
  status: string;
  notes: string;
  data: Record<string, unknown>;
  approved_at: string | null;
  updated_at: string;
};

export type ReviewedClientState = {
  schema_version: string;
  household: Record<string, unknown>;
  people: Array<Record<string, unknown>>;
  accounts: Array<Record<string, unknown>>;
  goals: Array<Record<string, unknown>>;
  goal_account_links: Array<Record<string, unknown>>;
  risk: Record<string, unknown>;
  planning: Record<string, unknown>;
  behavioral_notes: Record<string, unknown>;
  unknowns: Array<Record<string, unknown> | string>;
  conflicts: Array<Record<string, unknown>>;
  source_summary: Array<Record<string, unknown>>;
  readiness: Readiness;
};

export type ReviewWorkspaceSummary = {
  id: number;
  external_id: string;
  label: string;
  status: string;
  data_origin: string;
  readiness: Partial<Readiness>;
  document_count: number;
  created_at: string;
  updated_at: string;
};

export type ReviewWorkspace = ReviewWorkspaceSummary & {
  owner_email: string | null;
  linked_household_id: string | null;
  reviewed_state: Partial<ReviewedClientState>;
  match_candidates: MatchCandidate[];
  documents: ReviewDocument[];
  processing_jobs: ProcessingJob[];
  section_approvals: SectionApproval[];
  worker_health: {
    status: string;
    name?: string;
    last_seen_at: string | null;
    active_job_count: number;
  };
  timeline: Array<{
    id: number;
    action: string;
    entity_type: string;
    entity_id: string;
    metadata: Record<string, unknown>;
    created_at: string;
  }>;
};

export type ExtractedFact = {
  id: number;
  document_id: number;
  document_name: string;
  document_type: string;
  field: string;
  value: unknown;
  asserted_at: string | null;
  confidence: string;
  derivation_method: string;
  source_page: number | null;
  source_location: string;
  evidence_quote: string;
  extraction_run_id: string;
  is_current: boolean;
  created_at: string;
};

export type MatchCandidate = {
  household_id: string;
  display_name: string;
  confidence: number;
  reasons: string[];
};
