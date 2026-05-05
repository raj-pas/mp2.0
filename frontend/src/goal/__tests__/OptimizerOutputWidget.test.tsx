/**
 * OptimizerOutputWidget — engine-first improvement % consumption with
 * calibration fallback + slider-drag UX (Phase A3, locked §3.1, §3.5).
 *
 * Decision tree:
 *   isPreviewingOverride=true                              → calibration_drag pill
 *   household.latest_portfolio_run.link_recommendations[] → engine pill
 *                                                            (improvement_pct
 *                                                             dollar-weighted
 *                                                             across links)
 *   else (no engine links)                                → calibration pill
 *
 * react-i18next is mocked in `src/test/setup.ts` to return the key itself;
 * assertions target i18n keys.
 */
import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { OptimizerOutputWidget } from "../OptimizerOutputWidget";
import {
  mockEngineOutput,
  mockHousehold,
  mockLinkRecommendation,
  mockPortfolioRun,
} from "../../__tests__/__fixtures__/household";

// Mock useOptimizerOutput so calibration path is deterministic.
const optimizerState = {
  isPending: false as boolean,
  isError: false as boolean,
  data: undefined as
    | undefined
    | {
        ideal_low: number;
        current_low: number;
        improvement_pct: number;
        effective_score_1_5: 1 | 2 | 3 | 4 | 5;
        effective_descriptor: string;
        p_used: number;
        tier: "need" | "want" | "wish" | "unsure";
      },
};

vi.mock("../../lib/preview", () => ({
  useOptimizerOutput: () => ({
    get isPending() {
      return optimizerState.isPending;
    },
    get isError() {
      return optimizerState.isError;
    },
    get data() {
      return optimizerState.data;
    },
  }),
}));

beforeEach(() => {
  // Reset to known good calibration state per test
  optimizerState.isPending = false;
  optimizerState.isError = false;
  optimizerState.data = {
    ideal_low: 100000,
    current_low: 90000,
    improvement_pct: 5.0, // 5% (backend ships pct-scale per preview_views.py:476)
    effective_score_1_5: 3,
    effective_descriptor: "balanced",
    p_used: 0.05,
    tier: "want",
  };
});

describe("OptimizerOutputWidget — engine path", () => {
  it("renders engine pill + engine-derived improvement when link_recommendations exist", () => {
    // Engine: ideal 8% return; current 3% return; expected improvement = 5pp.
    // Different from calibration's 5% baseline so we can distinguish the source.
    const link = mockLinkRecommendation({
      goal_id: "goal_a",
      allocated_amount: 100000,
      expected_return: 0.08,
      current_comparison: {
        missing_holdings: false,
        status: "mapped",
        reason: "Current holdings mapped.",
        expected_return: 0.03,
        volatility: 0.04,
        allocations: [],
        deltas: [],
        holdings_diagnostics: [],
        unmapped_holdings: [],
        warnings: [],
      },
    });
    const household = mockHousehold({
      latest_portfolio_run: mockPortfolioRun({
        run_signature: "engine_sig_aaaa1111",
        output: mockEngineOutput({ link_recommendations: [link] }),
      }),
    });
    render(
      <OptimizerOutputWidget
        householdId="hh_test"
        goalId="goal_a"
        household={household}
        isPreviewingOverride={false}
      />,
    );
    expect(screen.getByText("goal_allocation.from_run")).toBeInTheDocument();
    // 8-char run signature prefix shown
    expect(screen.getByText(/engine_s/)).toBeInTheDocument();
    // Engine-derived improvement_pct = 0.08 - 0.03 = 0.05 → formatted "5.0%"
    expect(screen.getByText(/5\.0%/)).toBeInTheDocument();
  });

  it("uses link.expected_return as 'current' baseline when current_comparison.expected_return is null", () => {
    // When current_comparison.expected_return is null, the engine path should
    // fall back to link.expected_return so improvement degenerates to 0.
    const link = mockLinkRecommendation({
      goal_id: "goal_a",
      allocated_amount: 100000,
      expected_return: 0.07,
      current_comparison: {
        missing_holdings: false,
        status: "mapped",
        reason: "Current holdings mapped.",
        expected_return: null,
        volatility: null,
        allocations: [],
        deltas: [],
        holdings_diagnostics: [],
        unmapped_holdings: [],
        warnings: [],
      },
    });
    const household = mockHousehold({
      latest_portfolio_run: mockPortfolioRun({
        output: mockEngineOutput({ link_recommendations: [link] }),
      }),
    });
    render(
      <OptimizerOutputWidget
        householdId="hh_test"
        goalId="goal_a"
        household={household}
        isPreviewingOverride={false}
      />,
    );
    expect(screen.getByText("goal_allocation.from_run")).toBeInTheDocument();
    // 0.07 - 0.07 = 0 → formatted "0.0%"
    expect(screen.getByText(/0\.0%/)).toBeInTheDocument();
  });

  it("dollar-weights the improvement blend across multiple links", () => {
    // Link 1: $100k @ ideal 10%, current 5% → +5pp
    // Link 2: $300k @ ideal 4%, current 2%  → +2pp
    // Dollar-weighted blend:
    //   ideal   = (0.10 * 100k + 0.04 * 300k) / 400k = 22k / 400k = 0.055
    //   current = (0.05 * 100k + 0.02 * 300k) / 400k = 11k / 400k = 0.0275
    //   improvement = 0.055 - 0.0275 = 0.0275 → "2.8%" (rounded to 1dp)
    const link1 = mockLinkRecommendation({
      link_id: "link_1",
      goal_id: "goal_multi",
      allocated_amount: 100000,
      expected_return: 0.1,
      current_comparison: {
        missing_holdings: false,
        status: "mapped",
        reason: "ok",
        expected_return: 0.05,
        volatility: 0.05,
        allocations: [],
        deltas: [],
        holdings_diagnostics: [],
        unmapped_holdings: [],
        warnings: [],
      },
    });
    const link2 = mockLinkRecommendation({
      link_id: "link_2",
      goal_id: "goal_multi",
      allocated_amount: 300000,
      expected_return: 0.04,
      current_comparison: {
        missing_holdings: false,
        status: "mapped",
        reason: "ok",
        expected_return: 0.02,
        volatility: 0.02,
        allocations: [],
        deltas: [],
        holdings_diagnostics: [],
        unmapped_holdings: [],
        warnings: [],
      },
    });
    const household = mockHousehold({
      latest_portfolio_run: mockPortfolioRun({
        output: mockEngineOutput({ link_recommendations: [link1, link2] }),
      }),
    });
    render(
      <OptimizerOutputWidget
        householdId="hh_test"
        goalId="goal_multi"
        household={household}
        isPreviewingOverride={false}
      />,
    );
    expect(screen.getByText("goal_allocation.from_run")).toBeInTheDocument();
    expect(screen.getByText(/2\.8%/)).toBeInTheDocument();
  });
});

describe("OptimizerOutputWidget — calibration fallback", () => {
  it("renders calibration pill + calibration improvement when no engine links exist", () => {
    // Engine output has links for a different goal; queried goal has none → fallback.
    const link = mockLinkRecommendation({ goal_id: "goal_other" });
    const household = mockHousehold({
      latest_portfolio_run: mockPortfolioRun({
        output: mockEngineOutput({ link_recommendations: [link] }),
      }),
    });
    render(
      <OptimizerOutputWidget
        householdId="hh_test"
        goalId="goal_a"
        household={household}
        isPreviewingOverride={false}
      />,
    );
    expect(screen.getByText("goal_allocation.from_calibration")).toBeInTheDocument();
    expect(screen.queryByText("goal_allocation.from_run")).not.toBeInTheDocument();
    // Calibration's 5% baseline shown (not engine path)
    expect(screen.getByText(/5\.0%/)).toBeInTheDocument();
  });

  it("does not throw when link_recommendations array is empty (falls to calibration)", () => {
    const household = mockHousehold({
      latest_portfolio_run: mockPortfolioRun({
        output: mockEngineOutput({ link_recommendations: [] }),
      }),
    });
    expect(() =>
      render(
        <OptimizerOutputWidget
          householdId="hh_test"
          goalId="goal_a"
          household={household}
          isPreviewingOverride={false}
        />,
      ),
    ).not.toThrow();
    expect(screen.getByText("goal_allocation.from_calibration")).toBeInTheDocument();
  });
});

describe("OptimizerOutputWidget — slider-drag (calibration_drag)", () => {
  it("flips to calibration_drag pill when isPreviewingOverride=true even if engine links exist", () => {
    const link = mockLinkRecommendation({
      goal_id: "goal_a",
      allocated_amount: 100000,
      expected_return: 0.08,
    });
    const household = mockHousehold({
      latest_portfolio_run: mockPortfolioRun({
        output: mockEngineOutput({ link_recommendations: [link] }),
      }),
    });
    render(
      <OptimizerOutputWidget
        householdId="hh_test"
        goalId="goal_a"
        household={household}
        isPreviewingOverride={true}
      />,
    );
    expect(screen.getByText("goal_allocation.from_calibration_drag")).toBeInTheDocument();
    // Engine pill NOT shown during drag
    expect(screen.queryByText("goal_allocation.from_run")).not.toBeInTheDocument();
    // Calibration's 5% baseline shown (drag path uses calibration)
    expect(screen.getByText(/5\.0%/)).toBeInTheDocument();
  });
});

describe("OptimizerOutputWidget — StrictMode (locked #64)", () => {
  it("does not infinite-loop or double-fire under React.StrictMode", () => {
    const link = mockLinkRecommendation({
      goal_id: "goal_a",
      allocated_amount: 100000,
      expected_return: 0.08,
      current_comparison: {
        missing_holdings: false,
        status: "mapped",
        reason: "ok",
        expected_return: 0.03,
        volatility: 0.04,
        allocations: [],
        deltas: [],
        holdings_diagnostics: [],
        unmapped_holdings: [],
        warnings: [],
      },
    });
    const household = mockHousehold({
      latest_portfolio_run: mockPortfolioRun({
        output: mockEngineOutput({ link_recommendations: [link] }),
      }),
    });
    expect(() => {
      render(
        <React.StrictMode>
          <OptimizerOutputWidget
            householdId="hh_test"
            goalId="goal_a"
            household={household}
            isPreviewingOverride={false}
          />
        </React.StrictMode>,
      );
    }).not.toThrow();
    expect(screen.getByText("goal_allocation.from_run")).toBeInTheDocument();
  });
});
