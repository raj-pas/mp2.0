/**
 * Centralized HouseholdDetail mock factories (sub-session #4 — locked #84).
 *
 * Defaults match the live Sandra/Mike Chen production payload byte-for-byte
 * (captured from /api/clients/hh_sandra_mike_chen/ on 2026-05-04).
 *
 * Per locked decision #55: fixtures must match production payload shape
 * (especially nested object/array shapes); the cost-key bug at 2bd77d3 was
 * a fixture-vs-payload drift caught only by an e2e run.
 *
 * Usage:
 *   mockHousehold()                                              -> fully populated default
 *   mockHousehold({ latest_portfolio_run: null,
 *                   latest_portfolio_failure: null })           -> cold-start
 *   mockHousehold({ latest_portfolio_run: null,
 *                   latest_portfolio_failure: mockFailure() })  -> failure state
 */
import type {
  Account,
  Allocation,
  EngineOutput,
  ExternalAssetRow,
  FanChartPoint,
  Goal,
  GoalAccountLink,
  Holding,
  HouseholdDetail,
  LinkRecommendation,
  Member,
  PortfolioGenerationFailure,
  PortfolioRun,
  ProjectionPoint,
  Rollup,
} from "../../lib/household";

export function mockAllocation(overrides: Partial<Allocation> = {}): Allocation {
  return {
    sleeve_id: "sh_equity",
    sleeve_name: "SH Equity",
    weight: 0.3163049589034366,
    fund_type: "building_block",
    asset_class_weights: { cash: 0.0, equity: 1.0, fixed_income: 0.0 },
    geography_weights: { us: 0.15, canada: 0.75, international: 0.1 },
    ...overrides,
  };
}

export function mockRollup(overrides: Partial<Rollup> = {}): Rollup {
  return {
    id: "hh_sandra_mike_chen",
    name: "Household",
    allocated_amount: 1308000.0,
    expected_return: 0.05852645696810835,
    volatility: 0.06896193182848497,
    allocations: [
      mockAllocation({
        sleeve_id: "sh_equity",
        sleeve_name: "SH Equity",
        weight: 0.3163049589034366,
      }),
      mockAllocation({
        sleeve_id: "sh_income",
        sleeve_name: "SH Income",
        weight: 0.5262251683125276,
      }),
      mockAllocation({
        sleeve_id: "sh_global_equity",
        sleeve_name: "SH Global Equity",
        weight: 0.062911008882981,
      }),
      mockAllocation({
        sleeve_id: "sh_savings",
        sleeve_name: "SH Savings",
        weight: 0.05081262488527431,
      }),
      mockAllocation({
        sleeve_id: "sh_global_small_cap_eq",
        sleeve_name: "SH Global Small-Cap Eq",
        weight: 0.04364906631380028,
      }),
      mockAllocation({
        sleeve_id: "sh_founders",
        sleeve_name: "SH Founders",
        weight: 9.717270198011035e-5,
      }),
    ],
    ...overrides,
  };
}

export function mockProjectionPoint(
  overrides: Partial<ProjectionPoint> = {},
): ProjectionPoint {
  return {
    year: 0,
    p10: 67996.4846126969,
    p50: 68000.20838737857,
    p90: 68003.93236598985,
    optimized_percentile_value: 0.0,
    ...overrides,
  };
}

export function mockFanChartPoint(
  overrides: Partial<FanChartPoint> = {},
): FanChartPoint {
  return {
    link_id: "d6df8d1a-9ba4-444f-bee0-aac1322532e2",
    goal_id: "goal_emma_education",
    year: 0,
    p10: 67996.4846126969,
    p50: 68000.20838737857,
    p90: 68003.93236598985,
    ...overrides,
  };
}

export function mockLinkRecommendation(
  overrides: Partial<LinkRecommendation> = {},
): LinkRecommendation {
  return {
    link_id: "d6df8d1a-9ba4-444f-bee0-aac1322532e2",
    goal_id: "goal_emma_education",
    goal_name: "Emma education",
    account_id: "acct_non_registered",
    account_type: "Non-Registered",
    allocated_amount: 68000.0,
    horizon_years: 1.3278576317590691,
    goal_risk_score: 1,
    frontier_percentile: 5,
    allocations: [
      mockAllocation({
        sleeve_id: "sh_savings",
        sleeve_name: "SH Savings",
        weight: 0.9773957845579235,
        asset_class_weights: { cash: 1.0, equity: 0.0, fixed_income: 0.0 },
        geography_weights: { us: 0.0, canada: 1.0, international: 0.0 },
      }),
    ],
    expected_return: 0.030654285714285696,
    volatility: 0.004273158064292937,
    projected_value: 70252.83937160025,
    projection: [
      mockProjectionPoint({ year: 0, optimized_percentile_value: 0.0 }),
      mockProjectionPoint({
        year: 1,
        p10: 69733.20397998187,
        p50: 70116.12954575209,
        p90: 70501.15786861007,
        optimized_percentile_value: 70252.83937160025,
      }),
    ],
    current_comparison: {
      missing_holdings: false,
      status: "mapped",
      reason: "Current holdings mapped to the active CMA fund universe.",
      expected_return: 0.030654285714285696,
      volatility: 0.004273158064292937,
      allocations: [],
      deltas: [],
      holdings_diagnostics: [],
      unmapped_holdings: [],
      warnings: [],
    },
    drift_flags: ["review_rebalance"],
    warnings: ["review_rebalance"],
    explanation: {
      risk: { scale: "1-5", goal_risk_score: 1, frontier_percentile: 5 },
    },
    advisor_summary:
      "Emma education in Non-Registered uses goal risk 1/5 over 1.3 years, optimizing the 5th percentile outcome on the active frontier.",
    technical_trace: {
      goal_id: "goal_emma_education",
      link_id: "d6df8d1a-9ba4-444f-bee0-aac1322532e2",
    },
    ...overrides,
  };
}

export function mockEngineOutput(
  overrides: Partial<EngineOutput> = {},
): EngineOutput {
  return {
    schema_version: "engine_output.link_first.v2",
    household_id: "hh_sandra_mike_chen",
    link_recommendations: [mockLinkRecommendation()],
    goal_rollups: [
      {
        id: "goal_emma_education",
        name: "Emma education",
        allocated_amount: 68000.0,
        expected_return: 0.030654285714285696,
        volatility: 0.004273158064292937,
        allocations: [
          mockAllocation({
            sleeve_id: "sh_savings",
            sleeve_name: "SH Savings",
            weight: 0.9773957845579235,
            asset_class_weights: {},
            geography_weights: {},
          }),
        ],
      },
    ],
    account_rollups: [],
    household_rollup: mockRollup(),
    fan_chart: [mockFanChartPoint()],
    audit_trace: { method: "percentile" },
    advisor_summary: "Generated 6 goal-account recommendations using CMA snapshot 1.",
    technical_trace: {
      schema_version: "engine_output.link_first.v2",
      cma_snapshot_id: "58e9acb2-6de5-444e-ab95-003a5e1388a3",
    },
    run_manifest: {
      run_signature:
        "62f8cf0615dcb157e34df1658e3fa3cf86108b4471308ed271cab2904f19f8b2",
      schema_version: "engine_run_manifest.v2",
    },
    warnings: ["review_rebalance", "synthetic_or_seeded_missing_provenance"],
    ...overrides,
  };
}

export function mockPortfolioRun(
  overrides: Partial<PortfolioRun> = {},
): PortfolioRun {
  return {
    id: 2,
    external_id: "4d54c980-3aff-458d-8ca9-373d777dcd8c",
    status: "current",
    as_of_date: "2026-05-04",
    cma_snapshot_id: "58e9acb2-6de5-444e-ab95-003a5e1388a3",
    engine_version: "default_cma_link_frontier_v2",
    advisor_summary: "Generated 6 goal-account recommendations using CMA snapshot 1.",
    warnings: ["review_rebalance", "synthetic_or_seeded_missing_provenance"],
    created_at: "2026-05-04T00:33:53.996597-05:00",
    run_signature:
      "62f8cf0615dcb157e34df1658e3fa3cf86108b4471308ed271cab2904f19f8b2",
    output: mockEngineOutput(),
    technical_trace: null,
    ...overrides,
  };
}

export function mockFailure(
  overrides: Partial<PortfolioGenerationFailure> = {},
): PortfolioGenerationFailure {
  return {
    action: "portfolio_run_failed",
    reason_code: "engine_unavailable",
    exception_summary: "Connection timeout to engine",
    occurred_at: "2026-05-04T00:33:50.000000-05:00",
    ...overrides,
  };
}

export function mockHolding(overrides: Partial<Holding> = {}): Holding {
  return {
    sleeve_id: "sh_equity",
    sleeve_name: "SH Equity",
    weight: 0.1,
    market_value: 10800.0,
    ...overrides,
  };
}

export function mockGoalAccountLink(
  overrides: Partial<GoalAccountLink> = {},
): GoalAccountLink {
  return {
    id: "d6df8d1a-9ba4-444f-bee0-aac1322532e2",
    goal_id: "goal_emma_education",
    account_id: "acct_non_registered",
    allocated_amount: 68000.0,
    allocated_pct: null,
    ...overrides,
  };
}

export function mockGoal(overrides: Partial<Goal> = {}): Goal {
  return {
    id: "goal_emma_education",
    name: "Emma education",
    target_amount: 80000.0,
    target_date: "2027-09-01",
    necessity_score: 5,
    current_funded_amount: 68000.0,
    contribution_plan: null,
    goal_risk_score: 1,
    status: "on_track",
    notes: "Short-horizon need for their daughter's first university years.",
    account_allocations: [mockGoalAccountLink()],
    ...overrides,
  };
}

export function mockAccount(overrides: Partial<Account> = {}): Account {
  return {
    id: "acct_non_registered",
    owner_person_id: "person_mike_chen",
    type: "Non-Registered",
    regulatory_objective: "growth_and_income",
    regulatory_time_horizon: "3-10y",
    regulatory_risk_rating: "medium",
    current_value: 108000.0,
    contribution_room: null,
    is_held_at_purpose: true,
    missing_holdings_confirmed: false,
    cash_state: "invested",
    holdings: [
      mockHolding({ sleeve_id: "sh_equity", sleeve_name: "SH Equity", weight: 0.1, market_value: 10800.0 }),
      mockHolding({ sleeve_id: "sh_income", sleeve_name: "SH Income", weight: 0.6, market_value: 64800.0 }),
      mockHolding({ sleeve_id: "sh_savings", sleeve_name: "SH Savings", weight: 0.3, market_value: 32400.0 }),
    ],
    ...overrides,
  };
}

export function mockMember(overrides: Partial<Member> = {}): Member {
  return {
    id: "person_mike_chen",
    name: "Mike Chen",
    dob: "1964-02-12",
    marital_status: "married",
    investment_knowledge: "medium",
    employment: null,
    pensions: null,
    ...overrides,
  };
}

export function mockExternalAsset(
  overrides: Partial<ExternalAssetRow> = {},
): ExternalAssetRow {
  return {
    type: "home",
    value: 950000,
    description: "Primary residence, approximate value",
    ...overrides,
  };
}

export function mockHousehold(
  overrides: Partial<HouseholdDetail> = {},
): HouseholdDetail {
  return {
    id: "hh_sandra_mike_chen",
    display_name: "Sandra & Mike Chen",
    household_type: "couple",
    household_risk_score: 3,
    goal_count: 3,
    total_assets: 1308000.0,
    external_assets: [mockExternalAsset()],
    notes: "Fully synthetic Phase 1 demo persona. No real client data.",
    members: [mockMember()],
    goals: [mockGoal()],
    accounts: [mockAccount()],
    latest_portfolio_run: mockPortfolioRun(),
    latest_portfolio_failure: null,
    readiness_blockers: [],
    portfolio_runs: [
      {
        ...mockPortfolioRun(),
        output: null,
        technical_trace: null,
      },
    ],
    ...overrides,
  };
}
