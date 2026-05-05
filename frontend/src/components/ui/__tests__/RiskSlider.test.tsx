/**
 * RiskSlider — regression test for `onPreviewChange` semantics.
 *
 * The Phase A2 wiring (sub-session #1 commit `c5a7e02`) lifted
 * `isOverrideDraft` from the slider to GoalRoute via `onPreviewChange`,
 * driving the `<SourcePill>` flip between engine and calibration_drag.
 *
 * The original `isOverrideDraft = selectedScore !== systemScore` semantic
 * was correct for the form-visibility use case (existing pre-A2 behavior)
 * but WRONG for the new SourcePill use case: when a goal already has a
 * SAVED override with a non-system score (e.g., system=3, override=1),
 * the page-load state is `selectedScore (=1) !== systemScore (=3)` →
 * `onPreviewChange(true)` fires on mount → SourcePill renders
 * `calibration_drag` instead of `engine` even though the advisor hasn't
 * touched the slider.
 *
 * The Vitest mocks for GoalAllocationSection didn't render RiskSlider
 * directly; the visual-verification baseline at `e2e/visual-verification
 * .spec.ts` (Phase A5 new test) caught this by rendering the live goal
 * route on Sandra/Mike's `goal_retirement_income` (which has a saved
 * override score=1 ≠ system=3).
 *
 * Fix: split the semantic. `isOverrideDraft` (existing) keeps its
 * "score differs from system" meaning so the SaveOverrideForm renders
 * on the saved-override view, AND a new `isDragPreview = selectedScore
 * !== effectiveScore` fires `onPreviewChange` only when the advisor is
 * actively dragging away from the saved/system effective score.
 */
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render } from "@testing-library/react";

import { RiskSlider } from "../RiskSlider";

// Mock useCreateOverride so the slider doesn't try to fetch.
vi.mock("../../../lib/preview", () => ({
  useCreateOverride: () => ({ mutate: vi.fn(), isPending: false }),
}));

// Mock toast helpers.
vi.mock("../../../lib/toast", () => ({
  toastError: vi.fn(),
  toastSuccess: vi.fn(),
}));

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("RiskSlider — onPreviewChange semantics (locked §3.1 + §3.7)", () => {
  it("fires onPreviewChange(false) on mount when no saved override exists (selectedScore === systemScore === effectiveScore)", () => {
    const onPreviewChange = vi.fn();
    render(
      <RiskSlider
        goalId="goal_a"
        systemScore={3}
        effectiveScore={3} // no override
        isOverridden={false}
        canEdit={true}
        onPreviewChange={onPreviewChange}
      />,
    );
    // The useEffect that fires onPreviewChange runs once on mount.
    expect(onPreviewChange).toHaveBeenLastCalledWith(false);
  });

  it("fires onPreviewChange(false) on mount when a SAVED override exists (effectiveScore != systemScore but no draft)", () => {
    // Regression guard for the Phase A2 bug: with system=3, override=1,
    // page load was firing onPreviewChange(true) → SourcePill flipped to
    // calibration_drag instead of engine on the saved-override view.
    const onPreviewChange = vi.fn();
    render(
      <RiskSlider
        goalId="goal_a"
        systemScore={3}
        effectiveScore={1} // saved override at 1 (Sandra/Mike retirement_income state)
        isOverridden={true}
        canEdit={true}
        onPreviewChange={onPreviewChange}
      />,
    );
    expect(onPreviewChange).toHaveBeenLastCalledWith(false);
  });
});
