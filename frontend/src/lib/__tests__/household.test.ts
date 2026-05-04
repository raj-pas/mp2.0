/**
 * household.ts helpers — engine→UI display A3.5/A4 (sub-session #4 Round 1).
 *
 * Tests the 3 lookups used by RecommendationBanner / AdvisorSummaryPanel /
 * HouseholdPortfolioPanel:
 *   - findGoalRollup(household, goalId)
 *   - findHouseholdRollup(household)
 *   - findGoalLinkRecommendations(household, goalId)
 *
 * Defensive null/undefined handling matters because:
 *   - HouseholdDetail.latest_portfolio_run is `PortfolioRun | null`
 *   - PortfolioRun.output is `EngineOutput | null` (a run can exist
 *     without an embedded output snapshot — see engine error rows).
 *   - useHousehold() may pass `undefined` while loading.
 */
import { describe, expect, it } from "vitest";

import {
  findGoalLinkRecommendations,
  findGoalRollup,
  findHouseholdRollup,
} from "../household";
import {
  mockEngineOutput,
  mockHousehold,
  mockLinkRecommendation,
  mockPortfolioRun,
  mockRollup,
} from "../../__tests__/__fixtures__/household";

describe("findGoalRollup", () => {
  it("returns null when household is undefined", () => {
    expect(findGoalRollup(undefined, "goal_emma_education")).toBeNull();
  });

  it("returns null when latest_portfolio_run is null", () => {
    const hh = mockHousehold({ latest_portfolio_run: null });
    expect(findGoalRollup(hh, "goal_emma_education")).toBeNull();
  });

  it("returns null when run.output is null", () => {
    const hh = mockHousehold({
      latest_portfolio_run: mockPortfolioRun({ output: null }),
    });
    expect(findGoalRollup(hh, "goal_emma_education")).toBeNull();
  });

  it("returns null when no goal_rollup matches the requested id", () => {
    const hh = mockHousehold();
    expect(findGoalRollup(hh, "goal_does_not_exist")).toBeNull();
  });

  it("returns the rollup matching the requested goal id", () => {
    const hh = mockHousehold();
    const rollup = findGoalRollup(hh, "goal_emma_education");
    expect(rollup).not.toBeNull();
    expect(rollup?.id).toBe("goal_emma_education");
    expect(rollup?.name).toBe("Emma education");
  });

  it("matches by id even when multiple rollups are present", () => {
    const hh = mockHousehold({
      latest_portfolio_run: mockPortfolioRun({
        output: mockEngineOutput({
          goal_rollups: [
            mockRollup({ id: "goal_a", name: "Goal A" }),
            mockRollup({ id: "goal_b", name: "Goal B" }),
            mockRollup({ id: "goal_c", name: "Goal C" }),
          ],
        }),
      }),
    });
    expect(findGoalRollup(hh, "goal_b")?.name).toBe("Goal B");
  });
});

describe("findHouseholdRollup", () => {
  it("returns null when household is undefined", () => {
    expect(findHouseholdRollup(undefined)).toBeNull();
  });

  it("returns null when latest_portfolio_run is null", () => {
    const hh = mockHousehold({ latest_portfolio_run: null });
    expect(findHouseholdRollup(hh)).toBeNull();
  });

  it("returns null when run.output is null", () => {
    const hh = mockHousehold({
      latest_portfolio_run: mockPortfolioRun({ output: null }),
    });
    expect(findHouseholdRollup(hh)).toBeNull();
  });

  it("returns the household_rollup when present", () => {
    const hh = mockHousehold();
    const rollup = findHouseholdRollup(hh);
    expect(rollup).not.toBeNull();
    expect(rollup?.id).toBe("hh_sandra_mike_chen");
    expect(rollup?.name).toBe("Household");
    expect(rollup?.allocated_amount).toBe(1308000.0);
  });
});

describe("findGoalLinkRecommendations", () => {
  it("returns empty array when household is undefined", () => {
    expect(findGoalLinkRecommendations(undefined, "goal_emma_education")).toEqual([]);
  });

  it("returns empty array when latest_portfolio_run is null", () => {
    const hh = mockHousehold({ latest_portfolio_run: null });
    expect(findGoalLinkRecommendations(hh, "goal_emma_education")).toEqual([]);
  });

  it("returns empty array when run.output is null", () => {
    const hh = mockHousehold({
      latest_portfolio_run: mockPortfolioRun({ output: null }),
    });
    expect(findGoalLinkRecommendations(hh, "goal_emma_education")).toEqual([]);
  });

  it("returns empty array when no recommendations match the goal id", () => {
    const hh = mockHousehold();
    expect(findGoalLinkRecommendations(hh, "goal_no_match")).toEqual([]);
  });

  it("filters link_recommendations by goal_id (single-link goal)", () => {
    const hh = mockHousehold();
    const links = findGoalLinkRecommendations(hh, "goal_emma_education");
    expect(links).toHaveLength(1);
    expect(links[0]?.goal_id).toBe("goal_emma_education");
  });

  it("returns multiple recommendations for a multi-link goal", () => {
    const hh = mockHousehold({
      latest_portfolio_run: mockPortfolioRun({
        output: mockEngineOutput({
          link_recommendations: [
            mockLinkRecommendation({
              link_id: "link_1",
              goal_id: "goal_retirement",
              account_id: "acct_rrsp_mike",
              account_type: "RRSP",
            }),
            mockLinkRecommendation({
              link_id: "link_2",
              goal_id: "goal_retirement",
              account_id: "acct_rrsp_sandra",
              account_type: "RRSP",
            }),
            mockLinkRecommendation({
              link_id: "link_3",
              goal_id: "goal_retirement",
              account_id: "acct_tfsa",
              account_type: "TFSA",
            }),
            // unrelated goal
            mockLinkRecommendation({
              link_id: "link_4",
              goal_id: "goal_other",
            }),
          ],
        }),
      }),
    });
    const links = findGoalLinkRecommendations(hh, "goal_retirement");
    expect(links).toHaveLength(3);
    expect(links.map((l) => l.account_id)).toEqual([
      "acct_rrsp_mike",
      "acct_rrsp_sandra",
      "acct_tfsa",
    ]);
  });

  it("preserves engine ordering of link_recommendations", () => {
    const hh = mockHousehold({
      latest_portfolio_run: mockPortfolioRun({
        output: mockEngineOutput({
          link_recommendations: [
            mockLinkRecommendation({ link_id: "alpha", goal_id: "g" }),
            mockLinkRecommendation({ link_id: "beta", goal_id: "g" }),
            mockLinkRecommendation({ link_id: "gamma", goal_id: "g" }),
          ],
        }),
      }),
    });
    const links = findGoalLinkRecommendations(hh, "g");
    expect(links.map((l) => l.link_id)).toEqual(["alpha", "beta", "gamma"]);
  });

  it("does not mutate the source array", () => {
    const hh = mockHousehold();
    const before = hh.latest_portfolio_run?.output?.link_recommendations.length;
    findGoalLinkRecommendations(hh, "goal_emma_education");
    findGoalLinkRecommendations(hh, "goal_other");
    const after = hh.latest_portfolio_run?.output?.link_recommendations.length;
    expect(after).toBe(before);
  });
});
