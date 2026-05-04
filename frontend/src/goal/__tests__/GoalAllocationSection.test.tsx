/**
 * GoalAllocationSection — engine-first ideal-mix consumption with
 * calibration fallback + slider-drag UX (Phase A2 / locked §3.1, §3.7).
 *
 * Decision tree:
 *   isPreviewingOverride=true                       → calibration_drag pill
 *   household.latest_portfolio_run.goal_rollups[id] → engine pill
 *   else (no rollup)                                → calibration pill
 *
 * react-i18next is mocked in `src/test/setup.ts` to return the key itself;
 * assertions target i18n keys.
 */
import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { GoalAllocationSection } from "../GoalAllocationSection";
import {
  mockAllocation,
  mockEngineOutput,
  mockGoal,
  mockHousehold,
  mockPortfolioRun,
  mockRollup,
} from "../../__tests__/__fixtures__/household";
import type { HouseholdDetail } from "../../lib/household";

// Mock useSleeveMix so calibration path is deterministic.
const sleeveMixState = {
  isPending: false as boolean,
  isError: false as boolean,
  data: {
    score_1_5: 3 as 1 | 2 | 3 | 4 | 5,
    reference_score: 3,
    mix: { sh_equity: 50, sh_income: 50 } as Record<string, number>,
    fund_names: { sh_equity: "SH Equity", sh_income: "SH Income" },
  } as { score_1_5: 1 | 2 | 3 | 4 | 5; reference_score: number; mix: Record<string, number>; fund_names: Record<string, string> } | undefined,
};

vi.mock("../../lib/preview", () => ({
  useSleeveMix: () => ({
    get isPending() {
      return sleeveMixState.isPending;
    },
    get isError() {
      return sleeveMixState.isError;
    },
    get data() {
      return sleeveMixState.data;
    },
  }),
}));

function householdWithEngineRollup(goalId: string): HouseholdDetail {
  return mockHousehold({
    latest_portfolio_run: mockPortfolioRun({
      run_signature: "engine_sig_1234abcd",
      output: mockEngineOutput({
        goal_rollups: [
          mockRollup({
            id: goalId,
            allocations: [
              mockAllocation({ sleeve_id: "sh_equity", weight: 0.7 }),
              mockAllocation({ sleeve_id: "sh_income", weight: 0.3 }),
            ],
          }),
        ],
      }),
    }),
  });
}

function householdWithoutEngineRollup(_goalId: string): HouseholdDetail {
  // Run exists but goal_rollups[goalId] is missing → fallback path
  return mockHousehold({
    latest_portfolio_run: mockPortfolioRun({
      run_signature: "engine_sig_5678feed",
      output: mockEngineOutput({
        goal_rollups: [
          // Different goal_id; the queried goalId has no rollup
          mockRollup({ id: "different_goal", allocations: [] }),
        ],
      }),
    }),
  });
}

beforeEach(() => {
  // Reset to known good calibration state per test
  sleeveMixState.isPending = false;
  sleeveMixState.isError = false;
  sleeveMixState.data = {
    score_1_5: 3,
    reference_score: 3,
    mix: { sh_equity: 50, sh_income: 50 },
    fund_names: { sh_equity: "SH Equity", sh_income: "SH Income" },
  };
});

describe("GoalAllocationSection — engine path", () => {
  it("renders engine pill + run signature when goal_rollups[goal.id] exists", () => {
    const goal = mockGoal({ id: "goal_a" });
    const household = householdWithEngineRollup(goal.id);
    render(
      <GoalAllocationSection
        goal={goal}
        household={household}
        effectiveScore={3}
        isPreviewingOverride={false}
      />,
    );
    expect(screen.getByText("goal_allocation.from_run")).toBeInTheDocument();
    // 8-char prefix of run_signature shown
    expect(screen.getByText(/engine_s/)).toBeInTheDocument();
    // Calibration variant NOT shown
    expect(screen.queryByText("goal_allocation.from_calibration")).not.toBeInTheDocument();
  });

  it("renders bars from goal_rollup.allocations (NOT from useSleeveMix calibration)", () => {
    const goal = mockGoal({ id: "goal_a" });
    const household = householdWithEngineRollup(goal.id);
    // Distinct calibration data so we can verify engine path was taken
    sleeveMixState.data = {
      score_1_5: 3,
      reference_score: 3,
      mix: { sh_equity: 99, sh_income: 1 },
      fund_names: { sh_equity: "SH Equity", sh_income: "SH Income" },
    };
    render(
      <GoalAllocationSection
        goal={goal}
        household={household}
        effectiveScore={3}
        isPreviewingOverride={false}
      />,
    );
    // Engine path uses {sh_equity: 70%, sh_income: 30%} (from rollup)
    // not {sh_equity: 99%, sh_income: 1%} (calibration). Verify via
    // the rendered table; one of the visible percentages should be the engine value.
    // The actual rendered percent text uses formatPct (e.g., "70.0%").
    expect(screen.getByText(/70\.0%/)).toBeInTheDocument();
    expect(screen.queryByText(/99\.0%/)).not.toBeInTheDocument();
  });
});

describe("GoalAllocationSection — calibration fallback (no engine rollup)", () => {
  it("renders calibration pill when latest_portfolio_run is null", () => {
    const goal = mockGoal({ id: "goal_a" });
    const household = mockHousehold({ latest_portfolio_run: null });
    render(
      <GoalAllocationSection
        goal={goal}
        household={household}
        effectiveScore={3}
        isPreviewingOverride={false}
      />,
    );
    expect(screen.getByText("goal_allocation.from_calibration")).toBeInTheDocument();
    expect(screen.queryByText("goal_allocation.from_run")).not.toBeInTheDocument();
  });

  it("renders calibration pill when run exists but no goal_rollup matches the goal_id", () => {
    const goal = mockGoal({ id: "goal_a" });
    const household = householdWithoutEngineRollup(goal.id);
    render(
      <GoalAllocationSection
        goal={goal}
        household={household}
        effectiveScore={3}
        isPreviewingOverride={false}
      />,
    );
    expect(screen.getByText("goal_allocation.from_calibration")).toBeInTheDocument();
  });
});

describe("GoalAllocationSection — slider-drag (calibration_drag)", () => {
  it("flips to calibration_drag pill when isPreviewingOverride=true even if engine rollup exists", () => {
    const goal = mockGoal({ id: "goal_a" });
    const household = householdWithEngineRollup(goal.id);
    render(
      <GoalAllocationSection
        goal={goal}
        household={household}
        effectiveScore={3}
        isPreviewingOverride={true}
      />,
    );
    expect(screen.getByText("goal_allocation.from_calibration_drag")).toBeInTheDocument();
    // Engine pill NOT shown during drag
    expect(screen.queryByText("goal_allocation.from_run")).not.toBeInTheDocument();
  });

  it("uses calibration data (not engine data) during drag preview", () => {
    const goal = mockGoal({ id: "goal_a" });
    const household = householdWithEngineRollup(goal.id);
    sleeveMixState.data = {
      score_1_5: 4,
      reference_score: 4,
      mix: { sh_equity: 80, sh_income: 20 },
      fund_names: { sh_equity: "SH Equity", sh_income: "SH Income" },
    };
    render(
      <GoalAllocationSection
        goal={goal}
        household={household}
        effectiveScore={4}
        isPreviewingOverride={true}
      />,
    );
    // Calibration values shown during drag (80%/20%)
    expect(screen.getByText(/80\.0%/)).toBeInTheDocument();
  });
});

describe("GoalAllocationSection — error/loading states", () => {
  it("renders calibration error state when no engine rollup AND useSleeveMix errors", () => {
    const goal = mockGoal({ id: "goal_a" });
    const household = mockHousehold({ latest_portfolio_run: null });
    sleeveMixState.isError = true;
    sleeveMixState.data = undefined;
    render(
      <GoalAllocationSection
        goal={goal}
        household={household}
        effectiveScore={3}
        isPreviewingOverride={false}
      />,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("errors.preview_failed")).toBeInTheDocument();
  });

  it("does NOT render calibration error/skeleton when engine rollup exists (no calibration query needed)", () => {
    const goal = mockGoal({ id: "goal_a" });
    const household = householdWithEngineRollup(goal.id);
    sleeveMixState.isError = true;
    sleeveMixState.data = undefined;
    render(
      <GoalAllocationSection
        goal={goal}
        household={household}
        effectiveScore={3}
        isPreviewingOverride={false}
      />,
    );
    // Engine path renders bars even when calibration query fails
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByText("goal_allocation.from_run")).toBeInTheDocument();
  });
});

describe("GoalAllocationSection — StrictMode (locked #64)", () => {
  it("does not infinite-loop or double-fire under React.StrictMode", () => {
    const goal = mockGoal({ id: "goal_a" });
    const household = householdWithEngineRollup(goal.id);
    expect(() => {
      render(
        <React.StrictMode>
          <GoalAllocationSection
            goal={goal}
            household={household}
            effectiveScore={3}
            isPreviewingOverride={false}
          />
        </React.StrictMode>,
      );
    }).not.toThrow();
    expect(screen.getByText("goal_allocation.from_run")).toBeInTheDocument();
  });
});
