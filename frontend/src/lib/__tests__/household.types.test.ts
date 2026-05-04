/**
 * Type-level contracts for `lib/household.ts` (locked decision #104).
 *
 * Codified contracts that, if broken, would silently corrupt the engine→UI
 * display surfaces. These tests run at compile time via `expectTypeOf`; if
 * the types drift the file fails `tsc --noEmit` AND the vitest run.
 *
 * Background: `frontend/src/lib/api-types.ts` is OpenAPI-generated, but
 * HouseholdDetailSerializer + PortfolioRunSerializer aren't decorated yet
 * (post-pilot scope per the comment in household.ts). These hand-written
 * type tests are the safety net until codegen catches up.
 */
import { describe, expectTypeOf, it } from "vitest";

import type {
  Allocation,
  EngineOutput,
  ExternalAssetRow,
  FanChartPoint,
  Goal,
  GoalAccountLink,
  Holding,
  HouseholdDetail,
  LinkRecommendation,
  PortfolioGenerationFailure,
  PortfolioRun,
  ProjectionPoint,
  Rollup,
} from "../household";

describe("Allocation type contract", () => {
  it("weight is number", () => {
    expectTypeOf<Allocation["weight"]>().toEqualTypeOf<number>();
  });

  it("fund_type is the literal building_block | whole_portfolio union", () => {
    expectTypeOf<Allocation["fund_type"]>().toEqualTypeOf<
      "building_block" | "whole_portfolio"
    >();
  });

  it("asset_class_weights is Record<string, number>", () => {
    expectTypeOf<Allocation["asset_class_weights"]>().toEqualTypeOf<
      Record<string, number>
    >();
  });
});

describe("Rollup type contract", () => {
  it("allocations is Allocation[]", () => {
    expectTypeOf<Rollup["allocations"]>().toEqualTypeOf<Allocation[]>();
  });

  it("expected_return + volatility are number (NOT nullable)", () => {
    expectTypeOf<Rollup["expected_return"]>().toEqualTypeOf<number>();
    expectTypeOf<Rollup["volatility"]>().toEqualTypeOf<number>();
  });

  it("allocated_amount is number", () => {
    expectTypeOf<Rollup["allocated_amount"]>().toEqualTypeOf<number>();
  });
});

describe("EngineOutput type contract", () => {
  it("schema_version is the literal engine_output.link_first.v2", () => {
    expectTypeOf<EngineOutput["schema_version"]>().toEqualTypeOf<
      "engine_output.link_first.v2"
    >();
  });

  it("link_recommendations is LinkRecommendation[]", () => {
    expectTypeOf<EngineOutput["link_recommendations"]>().toEqualTypeOf<
      LinkRecommendation[]
    >();
  });

  it("goal_rollups + account_rollups are Rollup[]", () => {
    expectTypeOf<EngineOutput["goal_rollups"]>().toEqualTypeOf<Rollup[]>();
    expectTypeOf<EngineOutput["account_rollups"]>().toEqualTypeOf<Rollup[]>();
  });

  it("household_rollup is a single Rollup (NOT nullable)", () => {
    expectTypeOf<EngineOutput["household_rollup"]>().toEqualTypeOf<Rollup>();
  });

  it("fan_chart is FanChartPoint[]", () => {
    expectTypeOf<EngineOutput["fan_chart"]>().toEqualTypeOf<FanChartPoint[]>();
  });
});

describe("LinkRecommendation type contract", () => {
  it("advisor_summary is string", () => {
    expectTypeOf<LinkRecommendation["advisor_summary"]>().toEqualTypeOf<string>();
  });

  it("goal_risk_score is the canon 1-5 union", () => {
    expectTypeOf<LinkRecommendation["goal_risk_score"]>().toEqualTypeOf<1 | 2 | 3 | 4 | 5>();
  });

  it("projection is ProjectionPoint[]", () => {
    expectTypeOf<LinkRecommendation["projection"]>().toEqualTypeOf<ProjectionPoint[]>();
  });

  it("warnings is string[]", () => {
    expectTypeOf<LinkRecommendation["warnings"]>().toEqualTypeOf<string[]>();
  });
});

describe("HouseholdDetail type contract", () => {
  it("latest_portfolio_run is PortfolioRun | null", () => {
    expectTypeOf<HouseholdDetail["latest_portfolio_run"]>().toEqualTypeOf<
      PortfolioRun | null
    >();
  });

  it("latest_portfolio_failure is PortfolioGenerationFailure | null", () => {
    expectTypeOf<HouseholdDetail["latest_portfolio_failure"]>().toEqualTypeOf<
      PortfolioGenerationFailure | null
    >();
  });

  it("portfolio_runs is PortfolioRun[]", () => {
    expectTypeOf<HouseholdDetail["portfolio_runs"]>().toEqualTypeOf<PortfolioRun[]>();
  });

  it("goals is Goal[] / accounts is Account[]", () => {
    expectTypeOf<HouseholdDetail["goals"]>().toEqualTypeOf<Goal[]>();
  });

  it("external_assets is ExternalAssetRow[]", () => {
    expectTypeOf<HouseholdDetail["external_assets"]>().toEqualTypeOf<
      ExternalAssetRow[]
    >();
  });
});

describe("PortfolioRun type contract", () => {
  it("output is EngineOutput | null (a run can exist without an embedded snapshot)", () => {
    expectTypeOf<PortfolioRun["output"]>().toEqualTypeOf<EngineOutput | null>();
  });

  it("run_signature is string", () => {
    expectTypeOf<PortfolioRun["run_signature"]>().toEqualTypeOf<string>();
  });
});

describe("PortfolioGenerationFailure type contract", () => {
  it("occurred_at is string | null (used by RecommendationBanner ref dedup)", () => {
    expectTypeOf<PortfolioGenerationFailure["occurred_at"]>().toEqualTypeOf<
      string | null
    >();
  });

  it("reason_code is string", () => {
    expectTypeOf<PortfolioGenerationFailure["reason_code"]>().toEqualTypeOf<string>();
  });
});

describe("Goal/Holding/GoalAccountLink contracts", () => {
  it("Goal.account_allocations is GoalAccountLink[]", () => {
    expectTypeOf<Goal["account_allocations"]>().toEqualTypeOf<GoalAccountLink[]>();
  });

  it("Holding.market_value is number", () => {
    expectTypeOf<Holding["market_value"]>().toEqualTypeOf<number>();
  });

  it("GoalAccountLink.allocated_pct is number | null", () => {
    expectTypeOf<GoalAccountLink["allocated_pct"]>().toEqualTypeOf<number | null>();
  });
});
