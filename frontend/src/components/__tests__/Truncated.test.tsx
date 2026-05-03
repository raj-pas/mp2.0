/**
 * Tier 3 polish coverage — Truncated component (§1.10).
 *
 * Tests:
 *   - text under the threshold renders as a bare span (no tooltip
 *     overhead)
 *   - text over the threshold renders ellipsis + a focusable button
 *     trigger with the full text in aria-label
 *   - className passes through both branches
 *   - default max=80 cutoff matches the spec
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Truncated } from "../Truncated";

describe("Truncated", () => {
  it("renders a bare span when text is at or below the threshold", () => {
    render(<Truncated text="short text" max={80} />);
    const span = screen.getByText("short text");
    expect(span.tagName.toLowerCase()).toBe("span");
    // No <button> trigger, no aria-label-bearing affordance
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("renders ellipsis + button trigger when text exceeds max", () => {
    const longText = "a".repeat(120);
    render(<Truncated text={longText} max={80} />);
    const trigger = screen.getByRole("button");
    expect(trigger).toBeInTheDocument();
    // Truncated copy ends with ellipsis
    expect(trigger.textContent).toContain("…");
    expect(trigger.textContent?.length).toBeLessThan(longText.length);
    // Full text exposed via aria-label so screen readers narrate it.
    expect(trigger.getAttribute("aria-label")).toBe(longText);
  });

  it("default max=80 cutoff matches spec", () => {
    const exactlyEighty = "a".repeat(80);
    const eightyOne = "a".repeat(81);
    const { rerender } = render(<Truncated text={exactlyEighty} />);
    // 80 chars: bare span
    expect(screen.queryByRole("button")).toBeNull();
    rerender(<Truncated text={eightyOne} />);
    // 81 chars: tooltip trigger
    expect(screen.getByRole("button")).toBeInTheDocument();
  });

  it("forwards className to the bare-span branch", () => {
    render(<Truncated text="short" className="text-danger" />);
    const span = screen.getByText("short");
    expect(span).toHaveClass("text-danger");
  });

  it("forwards className to the truncated-trigger branch", () => {
    render(<Truncated text={"x".repeat(200)} className="font-mono" />);
    const trigger = screen.getByRole("button");
    expect(trigger).toHaveClass("font-mono");
  });

  it("text length 0 does not crash", () => {
    render(<Truncated text="" />);
    // Renders the empty span; no crash.
    expect(screen.queryByRole("button")).toBeNull();
  });
});
