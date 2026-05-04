/**
 * MovesPanel — engine vs calibration source pill rendering (Phase A2,
 * locked §3.3).
 *
 * Backend signals via `query.data.source: "portfolio_run" | "calibration"`;
 * frontend wraps in SourcePill. Slider-drag overrides backend signal per
 * locked §3.1.
 */
import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { MovesPanel } from "../MovesPanel";
import {
  mockHousehold,
  mockPortfolioRun,
} from "../../__tests__/__fixtures__/household";

// Mock useMoves so we control source + moves data directly.
const movesState = {
  isPending: false as boolean,
  isError: false as boolean,
  data: undefined as
    | undefined
    | {
        moves: { action: "buy" | "sell"; fund_id: string; fund_name: string; amount: number }[];
        total_buy?: number;
        total_sell?: number;
        source?: "portfolio_run" | "calibration";
      },
};

vi.mock("../../lib/preview", () => ({
  useMoves: () => ({
    get isPending() {
      return movesState.isPending;
    },
    get isError() {
      return movesState.isError;
    },
    get data() {
      return movesState.data;
    },
  }),
}));

beforeEach(() => {
  movesState.isPending = false;
  movesState.isError = false;
  movesState.data = {
    moves: [{ action: "buy", fund_id: "sh_equity", fund_name: "SH Equity", amount: 1000 }],
    total_buy: 1000,
    total_sell: 0,
    source: "calibration",
  };
});

describe("MovesPanel — source pill", () => {
  it("renders engine pill when query.data.source === 'portfolio_run'", () => {
    if (movesState.data) movesState.data.source = "portfolio_run";
    const household = mockHousehold({
      latest_portfolio_run: mockPortfolioRun({ run_signature: "moves_sig_abcdef12" }),
    });
    render(
      <MovesPanel
        householdId="hh_test"
        goalId="goal_a"
        household={household}
        isPreviewingOverride={false}
      />,
    );
    expect(screen.getByText("goal_allocation.from_run")).toBeInTheDocument();
    // 8-char sig prefix shown
    expect(screen.getByText(/moves_si/)).toBeInTheDocument();
  });

  it("renders calibration pill when query.data.source === 'calibration'", () => {
    if (movesState.data) movesState.data.source = "calibration";
    render(<MovesPanel householdId="hh_test" goalId="goal_a" isPreviewingOverride={false} />);
    expect(screen.getByText("goal_allocation.from_calibration")).toBeInTheDocument();
    expect(screen.queryByText("goal_allocation.from_run")).not.toBeInTheDocument();
  });

  it("flips to calibration_drag pill when isPreviewingOverride=true regardless of backend source", () => {
    if (movesState.data) movesState.data.source = "portfolio_run"; // backend says engine
    const household = mockHousehold({
      latest_portfolio_run: mockPortfolioRun({ run_signature: "engine_sig_4444" }),
    });
    render(
      <MovesPanel
        householdId="hh_test"
        goalId="goal_a"
        household={household}
        isPreviewingOverride={true}
      />,
    );
    expect(screen.getByText("goal_allocation.from_calibration_drag")).toBeInTheDocument();
    expect(screen.queryByText("goal_allocation.from_run")).not.toBeInTheDocument();
  });

  it("defaults to calibration pill when query.data.source is absent (back-compat with old responses)", () => {
    if (movesState.data) {
      delete movesState.data.source;
    }
    render(<MovesPanel householdId="hh_test" goalId="goal_a" isPreviewingOverride={false} />);
    expect(screen.getByText("goal_allocation.from_calibration")).toBeInTheDocument();
  });
});
