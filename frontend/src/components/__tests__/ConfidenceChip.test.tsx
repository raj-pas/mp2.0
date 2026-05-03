/**
 * ConfidenceChip — pure-presentation unit tests (Phase 6 sub-session #4).
 *
 * Asserts the canonical Confidence triple ("high"/"medium"/"low") renders:
 *   - the right text label (i18n key, since `useTranslation` is identity-mocked)
 *   - the right CSS classes (color-coded badge)
 *   - the right `aria-label` (a11y discipline, WCAG 2.1 AA)
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ConfidenceChip } from "../ConfidenceChip";

describe("ConfidenceChip", () => {
  it("renders the high level with accent styling and aria label", () => {
    render(<ConfidenceChip level="high" />);
    const chip = screen.getByText("confidence.high");
    expect(chip).toBeInTheDocument();
    expect(chip).toHaveAttribute("aria-label", "confidence.aria_high");
    expect(chip).toHaveClass("text-accent-2");
    expect(chip).toHaveClass("bg-accent/15");
  });

  it("renders the medium level with muted styling and aria label", () => {
    render(<ConfidenceChip level="medium" />);
    const chip = screen.getByText("confidence.medium");
    expect(chip).toBeInTheDocument();
    expect(chip).toHaveAttribute("aria-label", "confidence.aria_medium");
    expect(chip).toHaveClass("text-muted");
    expect(chip).toHaveClass("bg-ink/5");
  });

  it("renders the low level with danger styling and aria label", () => {
    render(<ConfidenceChip level="low" />);
    const chip = screen.getByText("confidence.low");
    expect(chip).toBeInTheDocument();
    expect(chip).toHaveAttribute("aria-label", "confidence.aria_low");
    expect(chip).toHaveClass("text-danger");
    expect(chip).toHaveClass("bg-danger/10");
  });

  it("appends caller-supplied className and exposes role=status", () => {
    render(<ConfidenceChip level="high" className="ml-2 custom-flag" />);
    const chip = screen.getByRole("status");
    expect(chip).toHaveClass("ml-2");
    expect(chip).toHaveClass("custom-flag");
    // Built-in classes still applied alongside the caller's:
    expect(chip).toHaveClass("text-accent-2");
  });
});
