/**
 * HouseholdPortfolioPanel — engine→UI display A4 unit tests (sub-session #4 R1).
 *
 * Mirrors the RecommendationBanner failure pattern (locked #19):
 *   - Run + rollup present:   metrics + top 4 funds
 *   - Rollup null + failure:  inline error + Retry CTA + Sonner toast
 *   - Rollup null + no failure: cold-start CTA
 *
 * Per locked decisions:
 *   #19  HouseholdPortfolioPanel mirrors RecommendationBanner's failure flow.
 *   #64  StrictMode-double-invoke check.
 *   #109 aria-live="polite" on the status region.
 */
import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HouseholdPortfolioPanel } from "../HouseholdPortfolioPanel";
import {
  mockBlocker,
  mockEngineOutput,
  mockFailure,
  mockHousehold,
  mockPortfolioRun,
  mockRollup,
  mockAllocation,
} from "../../__tests__/__fixtures__/household";

const generateMutate = vi.fn();
const generatePending = { current: false };

vi.mock("../../lib/preview", () => ({
  useGeneratePortfolio: () => ({
    mutate: generateMutate,
    get isPending() {
      return generatePending.current;
    },
  }),
}));

const toastErrorMock = vi.fn();
vi.mock("../../lib/toast", () => ({
  toastError: (...args: unknown[]) => toastErrorMock(...args),
  toastSuccess: vi.fn(),
}));

beforeEach(() => {
  generateMutate.mockClear();
  toastErrorMock.mockClear();
  generatePending.current = false;
});

afterEach(() => {
  vi.useRealTimers();
});

describe("HouseholdPortfolioPanel — run present", () => {
  it("renders the household_rollup metrics + title", () => {
    render(<HouseholdPortfolioPanel household={mockHousehold()} />);
    expect(
      screen.getByRole("heading", { name: /routes\.household\.portfolio_panel_title/ }),
    ).toBeInTheDocument();
  });

  it("status region has aria-live='polite' (locked #109)", () => {
    render(<HouseholdPortfolioPanel household={mockHousehold()} />);
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
  });

  it("shows expected_return as a percent string", () => {
    const hh = mockHousehold({
      latest_portfolio_run: mockPortfolioRun({
        output: mockEngineOutput({
          household_rollup: mockRollup({
            expected_return: 0.0585,
            volatility: 0.069,
            allocations: [mockAllocation()],
          }),
        }),
      }),
    });
    render(<HouseholdPortfolioPanel household={hh} />);
    // formatPct(5.85) -> "5.9%"
    expect(screen.getByText(/5\.9%/)).toBeInTheDocument();
  });

  it("shows volatility as a percent string", () => {
    const hh = mockHousehold({
      latest_portfolio_run: mockPortfolioRun({
        output: mockEngineOutput({
          household_rollup: mockRollup({
            expected_return: 0.06,
            volatility: 0.0689,
            allocations: [mockAllocation()],
          }),
        }),
      }),
    });
    render(<HouseholdPortfolioPanel household={hh} />);
    // formatPct(6.89) -> "6.9%"
    expect(screen.getByText(/6\.9%/)).toBeInTheDocument();
  });

  it("renders the top 4 funds sorted by weight desc (truncates the rest)", () => {
    const hh = mockHousehold({
      latest_portfolio_run: mockPortfolioRun({
        output: mockEngineOutput({
          household_rollup: mockRollup({
            allocations: [
              mockAllocation({ sleeve_id: "f1", sleeve_name: "F1", weight: 0.05 }),
              mockAllocation({ sleeve_id: "f2", sleeve_name: "F2", weight: 0.50 }),
              mockAllocation({ sleeve_id: "f3", sleeve_name: "F3", weight: 0.15 }),
              mockAllocation({ sleeve_id: "f4", sleeve_name: "F4", weight: 0.20 }),
              mockAllocation({ sleeve_id: "f5", sleeve_name: "F5", weight: 0.10 }),
            ],
          }),
        }),
      }),
    });
    render(<HouseholdPortfolioPanel household={hh} />);
    // Top 4 by weight desc: F2 (0.50), F4 (0.20), F3 (0.15), F5 (0.10)
    expect(screen.getByText("F2")).toBeInTheDocument();
    expect(screen.getByText("F4")).toBeInTheDocument();
    expect(screen.getByText("F3")).toBeInTheDocument();
    expect(screen.getByText("F5")).toBeInTheDocument();
    // F1 (0.05) is the 5th — should NOT render
    expect(screen.queryByText("F1")).not.toBeInTheDocument();
  });

  it("does not fire any toast when run is present", () => {
    render(<HouseholdPortfolioPanel household={mockHousehold()} />);
    expect(toastErrorMock).not.toHaveBeenCalled();
  });
});

describe("HouseholdPortfolioPanel — cold start (no run + no failure)", () => {
  it("renders Generate CTA + cold-start copy", () => {
    const hh = mockHousehold({
      latest_portfolio_run: null,
      latest_portfolio_failure: null,
    });
    render(<HouseholdPortfolioPanel household={hh} />);
    expect(
      screen.getByRole("button", { name: /routes\.household\.generate/i }),
    ).toBeInTheDocument();
  });

  it("aria-live='polite' on cold-start status region", () => {
    const hh = mockHousehold({
      latest_portfolio_run: null,
      latest_portfolio_failure: null,
    });
    render(<HouseholdPortfolioPanel household={hh} />);
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
  });

  it("clicking Generate fires the mutation", () => {
    const hh = mockHousehold({
      latest_portfolio_run: null,
      latest_portfolio_failure: null,
    });
    render(<HouseholdPortfolioPanel household={hh} />);
    fireEvent.click(
      screen.getByRole("button", { name: /routes\.household\.generate/i }),
    );
    expect(generateMutate).toHaveBeenCalledTimes(1);
  });

  it("StrictMode double-invoke: mutation fires once per click", () => {
    const hh = mockHousehold({
      latest_portfolio_run: null,
      latest_portfolio_failure: null,
    });
    render(
      <React.StrictMode>
        <HouseholdPortfolioPanel household={hh} />
      </React.StrictMode>,
    );
    fireEvent.click(
      screen.getByRole("button", { name: /routes\.household\.generate/i }),
    );
    expect(generateMutate).toHaveBeenCalledTimes(1);
  });
});

describe("HouseholdPortfolioPanel — failure state (mirrors RecommendationBanner #19)", () => {
  it("renders inline failure copy + Retry CTA when run is null + failure present", () => {
    const hh = mockHousehold({
      latest_portfolio_run: null,
      latest_portfolio_failure: mockFailure({ reason_code: "engine_unavailable" }),
    });
    render(<HouseholdPortfolioPanel household={hh} />);
    expect(
      screen.getByRole("button", { name: /routes\.household\.retry/i }),
    ).toBeInTheDocument();
  });

  it("aria-live='polite' on failure status region (locked #109)", () => {
    const hh = mockHousehold({
      latest_portfolio_run: null,
      latest_portfolio_failure: mockFailure(),
    });
    render(<HouseholdPortfolioPanel household={hh} />);
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
  });

  it("fires Sonner toast on mount when failure is present (locked #9)", () => {
    const hh = mockHousehold({
      latest_portfolio_run: null,
      latest_portfolio_failure: mockFailure({ reason_code: "engine_unavailable" }),
    });
    render(<HouseholdPortfolioPanel household={hh} />);
    expect(toastErrorMock).toHaveBeenCalledTimes(1);
    expect(toastErrorMock).toHaveBeenCalledWith(
      "routes.household.generation_failed_title",
      expect.objectContaining({
        description: "routes.household.generation_failed_body",
      }),
    );
  });

  it("dedups the toast on re-render (lastSurfacedRef tracks occurred_at)", () => {
    const failure = mockFailure({ occurred_at: "2026-05-04T00:00:00Z" });
    const hh = mockHousehold({
      latest_portfolio_run: null,
      latest_portfolio_failure: failure,
    });
    const { rerender } = render(<HouseholdPortfolioPanel household={hh} />);
    rerender(<HouseholdPortfolioPanel household={hh} />);
    rerender(<HouseholdPortfolioPanel household={hh} />);
    expect(toastErrorMock).toHaveBeenCalledTimes(1);
  });

  it("clicking Retry fires the mutation", () => {
    const hh = mockHousehold({
      latest_portfolio_run: null,
      latest_portfolio_failure: mockFailure(),
    });
    render(<HouseholdPortfolioPanel household={hh} />);
    fireEvent.click(
      screen.getByRole("button", { name: /routes\.household\.retry/i }),
    );
    expect(generateMutate).toHaveBeenCalledTimes(1);
  });

  it("disables Retry while mutation is pending", () => {
    generatePending.current = true;
    const hh = mockHousehold({
      latest_portfolio_run: null,
      latest_portfolio_failure: mockFailure(),
    });
    render(<HouseholdPortfolioPanel household={hh} />);
    expect(
      screen.getByRole("button", { name: /routes\.household\.regenerating/i }),
    ).toBeDisabled();
  });
});

describe("HouseholdPortfolioPanel — stale variants (post-tag locked §3.2 + §3.4)", () => {
  it("renders stale chip + Regenerate for status='invalidated'", () => {
    const hh = mockHousehold({
      latest_portfolio_run: mockPortfolioRun({ status: "invalidated" }),
    });
    render(<HouseholdPortfolioPanel household={hh} />);
    expect(screen.getByText("routes.household.stale_chip_label")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /routes\.household\.regenerate/i }),
    ).toBeInTheDocument();
    // aria-live preserved (status region, locked #109)
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
  });

  it("renders stale chip + Regenerate for status='superseded'", () => {
    const hh = mockHousehold({
      latest_portfolio_run: mockPortfolioRun({ status: "superseded" }),
    });
    render(<HouseholdPortfolioPanel household={hh} />);
    expect(screen.getByText("routes.household.stale_chip_label")).toBeInTheDocument();
  });

  it("renders integrity chip with role='alert' and NO Regenerate for status='hash_mismatch'", () => {
    const hh = mockHousehold({
      latest_portfolio_run: mockPortfolioRun({ status: "hash_mismatch" }),
    });
    render(<HouseholdPortfolioPanel household={hh} />);
    expect(screen.getByText("routes.household.integrity_chip_label")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /routes\.household\.regenerate/i }),
    ).not.toBeInTheDocument();
    // role='alert' — engineering attention; not role='status'
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("clicking stale Regenerate fires the mutation exactly once", () => {
    const hh = mockHousehold({
      latest_portfolio_run: mockPortfolioRun({ status: "declined" }),
    });
    render(<HouseholdPortfolioPanel household={hh} />);
    fireEvent.click(
      screen.getByRole("button", { name: /routes\.household\.regenerate/i }),
    );
    expect(generateMutate).toHaveBeenCalledTimes(1);
  });
});

// ---------------------------------------------------------------------------
// P11 — structured portfolio-readiness blockers (plan v20 §A1.27)
// ---------------------------------------------------------------------------

describe("HouseholdPortfolioPanel — structured blockers (P11)", () => {
  it("renders the StructuredBlockerBanner when structured_readiness_blockers has entries", () => {
    const hh = mockHousehold({
      latest_portfolio_run: null,
      latest_portfolio_failure: null,
      structured_readiness_blockers: [
        mockBlocker({
          code: "purpose_account_unassigned",
          account_label: "Purpose RRSP at Steadyhand ($890K)",
          ui_action: "assign_to_goal",
        }),
      ],
    });
    render(<HouseholdPortfolioPanel household={hh} />);
    expect(screen.getByTestId("structured-blocker-banner")).toBeInTheDocument();
  });

  it("renders one fix-CTA button per blocker (Round 9 #11 LOCKED — no bypass)", () => {
    const hh = mockHousehold({
      latest_portfolio_run: null,
      latest_portfolio_failure: null,
      structured_readiness_blockers: [
        mockBlocker({
          code: "purpose_account_unassigned",
          ui_action: "assign_to_goal",
        }),
        mockBlocker({
          code: "goal_missing_target_date",
          goal_id: "g_x",
          goal_label: "Retirement",
          ui_action: "set_goal_horizon",
        }),
        mockBlocker({
          code: "household_invalid_risk_score",
          account_id: undefined,
          account_label: undefined,
          account_value_basis_points: undefined,
          ui_action: "set_household_risk",
        }),
      ],
    });
    render(<HouseholdPortfolioPanel household={hh} />);
    const banner = screen.getByTestId("structured-blocker-banner");
    // 3 blockers → 3 fix-CTA buttons inside the banner.
    const buttons = banner.querySelectorAll("button[data-ui-action]");
    expect(buttons).toHaveLength(3);
    expect(buttons[0]).toHaveAttribute("data-ui-action", "assign_to_goal");
    expect(buttons[1]).toHaveAttribute("data-ui-action", "set_goal_horizon");
    expect(buttons[2]).toHaveAttribute("data-ui-action", "set_household_risk");
  });

  it("falls back to humanized strings when structured_readiness_blockers is null (§3.16 backwards-compat)", () => {
    const hh = mockHousehold({
      latest_portfolio_run: null,
      latest_portfolio_failure: null,
      structured_readiness_blockers: null,
      readiness_blockers: ["Purpose account RRSP (acct_xxx) must be assigned to a goal."],
    });
    render(<HouseholdPortfolioPanel household={hh} />);
    expect(screen.queryByTestId("structured-blocker-banner")).not.toBeInTheDocument();
    expect(
      screen.getByText(/Purpose account RRSP \(acct_xxx\) must be assigned/i),
    ).toBeInTheDocument();
  });

  it("structured banner sits at z-10 (below sister's StaleRunOverlay z-20 per §A1.19 §3.2)", () => {
    const hh = mockHousehold({
      latest_portfolio_run: null,
      latest_portfolio_failure: null,
      structured_readiness_blockers: [mockBlocker()],
    });
    render(<HouseholdPortfolioPanel household={hh} />);
    const section = screen.getByRole("status");
    expect(section.className).toContain("z-10");
  });

  it("Generate button disabled when structured blockers present (locked #11 — no bypass)", () => {
    const hh = mockHousehold({
      latest_portfolio_run: null,
      latest_portfolio_failure: null,
      structured_readiness_blockers: [mockBlocker()],
    });
    render(<HouseholdPortfolioPanel household={hh} />);
    expect(
      screen.getByRole("button", { name: /routes\.household\.generate/i }),
    ).toBeDisabled();
  });
});

// Sister §A1.50 empty-state — falls back to humanized strings on empty.
describe("HouseholdPortfolioPanel — empty state fallback (§A1.50)", () => {
  it("test_blocker_banner_empty_state_falls_back_to_humanized_strings", () => {
    const hh = mockHousehold({
      latest_portfolio_run: null,
      latest_portfolio_failure: null,
      // Empty list (not null) → no banner, but humanized fallback only fires
      // when humanized list is also non-empty.
      structured_readiness_blockers: [],
      readiness_blockers: ["Legacy humanized blocker"],
    });
    render(<HouseholdPortfolioPanel household={hh} />);
    expect(screen.queryByTestId("structured-blocker-banner")).not.toBeInTheDocument();
    expect(screen.getByText(/Legacy humanized blocker/i)).toBeInTheDocument();
  });
});
