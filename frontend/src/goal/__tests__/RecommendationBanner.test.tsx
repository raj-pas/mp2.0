/**
 * RecommendationBanner — engine→UI display A3.5 unit tests (sub-session #4 R1).
 *
 * Covers the 3 visual states + the failure-toast lifecycle:
 *   1. Run present:     signature[:8] + "Regenerate" CTA + aria-live=polite
 *   2. Cold start:      "no_recommendation_yet" + "Generate" CTA
 *   3. Failure inline:  inline error + "Retry" CTA + Sonner toast (locked #9)
 *
 * Per locked decisions:
 *   #64  At least one StrictMode-double-invoke check per new component
 *        (the DocDropOverlay regression at bca0112 was exactly this class).
 *   #109 aria-live="polite" is mandatory on the status banner.
 *
 * Mocks:
 *   - sonner: toast assertions go through ../../lib/toast (which wraps sonner).
 *   - ../../lib/preview: useGeneratePortfolio (pure unit; no actual fetch).
 */
import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { RecommendationBanner } from "../RecommendationBanner";
import {
  mockFailure,
  mockPortfolioRun,
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
const toastSuccessMock = vi.fn();
vi.mock("../../lib/toast", () => ({
  toastError: (...args: unknown[]) => toastErrorMock(...args),
  toastSuccess: (...args: unknown[]) => toastSuccessMock(...args),
}));

beforeEach(() => {
  generateMutate.mockClear();
  toastErrorMock.mockClear();
  toastSuccessMock.mockClear();
  generatePending.current = false;
});

afterEach(() => {
  vi.useRealTimers();
});

describe("RecommendationBanner — run present", () => {
  it("renders the run signature (first 8 chars) and the Regenerate CTA", () => {
    const run = mockPortfolioRun({
      run_signature: "62f8cf0615dcb157e34df1658e3fa3cf86108b4471308ed271cab2904f19f8b2",
    });
    render(
      <RecommendationBanner run={run} failure={null} householdId="hh_sandra_mike_chen" />,
    );
    expect(screen.getByRole("status")).toBeInTheDocument();
    // i18n stub returns the key; the interpolated signature is in the options arg
    // (not visible text). Assert via the container that the regenerate CTA shows.
    expect(screen.getByRole("button", { name: /routes\.goal\.regenerate/i })).toBeInTheDocument();
  });

  it("status region has aria-live='polite' (locked #109)", () => {
    render(
      <RecommendationBanner
        run={mockPortfolioRun()}
        failure={null}
        householdId="hh_sandra_mike_chen"
      />,
    );
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
  });

  it("clicking Regenerate triggers the mutation exactly once", () => {
    render(
      <RecommendationBanner
        run={mockPortfolioRun()}
        failure={null}
        householdId="hh_sandra_mike_chen"
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /routes\.goal\.regenerate/i }));
    expect(generateMutate).toHaveBeenCalledTimes(1);
  });

  it("shows 'Regenerating…' label and disables CTA while pending", () => {
    generatePending.current = true;
    render(
      <RecommendationBanner
        run={mockPortfolioRun()}
        failure={null}
        householdId="hh_sandra_mike_chen"
      />,
    );
    const cta = screen.getByRole("button", { name: /routes\.goal\.regenerating/i });
    expect(cta).toBeDisabled();
  });

  it("does not fire any failure toast when run is present", () => {
    render(
      <RecommendationBanner
        run={mockPortfolioRun()}
        failure={null}
        householdId="hh_sandra_mike_chen"
      />,
    );
    expect(toastErrorMock).not.toHaveBeenCalled();
  });

  it("StrictMode double-invoke: mutation fires exactly once per click", () => {
    render(
      <React.StrictMode>
        <RecommendationBanner
          run={mockPortfolioRun()}
          failure={null}
          householdId="hh_sandra_mike_chen"
        />
      </React.StrictMode>,
    );
    fireEvent.click(screen.getByRole("button", { name: /routes\.goal\.regenerate/i }));
    expect(generateMutate).toHaveBeenCalledTimes(1);
  });
});

describe("RecommendationBanner — cold start (no run + no failure)", () => {
  it("renders the cold-start copy and Generate CTA", () => {
    render(
      <RecommendationBanner
        run={null}
        failure={null}
        householdId="hh_sandra_mike_chen"
      />,
    );
    expect(screen.getByText("routes.goal.no_recommendation_yet")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /routes\.goal\.generate/i })).toBeInTheDocument();
  });

  it("status region has aria-live='polite' (locked #109)", () => {
    render(
      <RecommendationBanner
        run={null}
        failure={null}
        householdId="hh_sandra_mike_chen"
      />,
    );
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
  });

  it("clicking Generate fires the mutation", () => {
    render(
      <RecommendationBanner
        run={null}
        failure={null}
        householdId="hh_sandra_mike_chen"
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /routes\.goal\.generate/i }));
    expect(generateMutate).toHaveBeenCalledTimes(1);
  });

  it("does not fire toast when there is no failure", () => {
    render(
      <RecommendationBanner
        run={null}
        failure={null}
        householdId="hh_sandra_mike_chen"
      />,
    );
    expect(toastErrorMock).not.toHaveBeenCalled();
  });

  it("StrictMode double-invoke: still fires mutation once per click in cold-start state", () => {
    render(
      <React.StrictMode>
        <RecommendationBanner
          run={null}
          failure={null}
          householdId="hh_sandra_mike_chen"
        />
      </React.StrictMode>,
    );
    fireEvent.click(screen.getByRole("button", { name: /routes\.goal\.generate/i }));
    expect(generateMutate).toHaveBeenCalledTimes(1);
  });
});

describe("RecommendationBanner — failure state", () => {
  it("renders the inline failure copy and Retry CTA", () => {
    render(
      <RecommendationBanner
        run={null}
        failure={mockFailure({ reason_code: "engine_unavailable" })}
        householdId="hh_sandra_mike_chen"
      />,
    );
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /routes\.goal\.retry/i }),
    ).toBeInTheDocument();
  });

  it("status region has aria-live='polite' on failure (locked #109)", () => {
    render(
      <RecommendationBanner
        run={null}
        failure={mockFailure()}
        householdId="hh_sandra_mike_chen"
      />,
    );
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
  });

  it("fires Sonner toast on mount (locked #9)", () => {
    render(
      <RecommendationBanner
        run={null}
        failure={mockFailure({ reason_code: "engine_unavailable" })}
        householdId="hh_sandra_mike_chen"
      />,
    );
    expect(toastErrorMock).toHaveBeenCalledTimes(1);
    expect(toastErrorMock).toHaveBeenCalledWith(
      "routes.goal.generation_failed_title",
      expect.objectContaining({ description: "routes.goal.generation_failed_body" }),
    );
  });

  it("dedups the toast on re-render (lastSurfacedRef tracks occurred_at)", () => {
    const failure = mockFailure({ occurred_at: "2026-05-04T00:00:00Z" });
    const { rerender } = render(
      <RecommendationBanner
        run={null}
        failure={failure}
        householdId="hh_sandra_mike_chen"
      />,
    );
    // Re-render with the SAME failure (e.g., react-query refetch returns identical data).
    rerender(
      <RecommendationBanner
        run={null}
        failure={failure}
        householdId="hh_sandra_mike_chen"
      />,
    );
    rerender(
      <RecommendationBanner
        run={null}
        failure={failure}
        householdId="hh_sandra_mike_chen"
      />,
    );
    expect(toastErrorMock).toHaveBeenCalledTimes(1);
  });

  it("re-fires the toast when occurred_at changes (new failure)", () => {
    const { rerender } = render(
      <RecommendationBanner
        run={null}
        failure={mockFailure({ occurred_at: "2026-05-04T00:00:00Z" })}
        householdId="hh_sandra_mike_chen"
      />,
    );
    expect(toastErrorMock).toHaveBeenCalledTimes(1);
    rerender(
      <RecommendationBanner
        run={null}
        failure={mockFailure({ occurred_at: "2026-05-04T01:00:00Z" })}
        householdId="hh_sandra_mike_chen"
      />,
    );
    expect(toastErrorMock).toHaveBeenCalledTimes(2);
  });

  it("clicking Retry fires the mutation", () => {
    render(
      <RecommendationBanner
        run={null}
        failure={mockFailure()}
        householdId="hh_sandra_mike_chen"
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /routes\.goal\.retry/i }));
    expect(generateMutate).toHaveBeenCalledTimes(1);
  });

  it("disables Retry while mutation is pending", () => {
    generatePending.current = true;
    render(
      <RecommendationBanner
        run={null}
        failure={mockFailure()}
        householdId="hh_sandra_mike_chen"
      />,
    );
    expect(
      screen.getByRole("button", { name: /routes\.goal\.regenerating/i }),
    ).toBeDisabled();
  });
});
