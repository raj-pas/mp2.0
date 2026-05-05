/**
 * StaleRunOverlay — bespoke modal focus model + 3 status copy variants
 * (Phase A4 / locked §3.2 + #18 + #68).
 *
 * Mirrors DocDetailPanel.tsx:56-67 focus-trap pattern (locked #68); Esc
 * does NOT dismiss (informational, not modal); Tab is trapped to the
 * Regenerate button (only focusable element).
 */
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import { StaleRunOverlay } from "../StaleRunOverlay";

describe("StaleRunOverlay — ARIA + focus model", () => {
  it("renders with role='alertdialog' + aria-modal + aria-labelledby + aria-describedby", () => {
    render(<StaleRunOverlay status="invalidated" onRegenerate={vi.fn()} isPending={false} />);
    const dialog = screen.getByRole("alertdialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveAttribute("aria-labelledby", "stale-overlay-title");
    expect(dialog).toHaveAttribute("aria-describedby", "stale-overlay-body");
  });

  it("auto-focuses the Regenerate button on mount", () => {
    render(<StaleRunOverlay status="invalidated" onRegenerate={vi.fn()} isPending={false} />);
    const button = screen.getByRole("button", {
      name: /routes\.goal\.stale_overlay_regenerate/i,
    });
    expect(button).toHaveFocus();
  });

  it("restores previous focus on unmount", () => {
    // Set up a "previous focus" target outside the overlay
    const previousButton = document.createElement("button");
    previousButton.textContent = "Outside";
    document.body.appendChild(previousButton);
    previousButton.focus();
    expect(previousButton).toHaveFocus();

    const { unmount } = render(
      <StaleRunOverlay status="invalidated" onRegenerate={vi.fn()} isPending={false} />,
    );
    // Overlay mounted → its button has focus
    expect(
      screen.getByRole("button", { name: /routes\.goal\.stale_overlay_regenerate/i }),
    ).toHaveFocus();

    unmount();
    // Focus restored
    expect(previousButton).toHaveFocus();

    document.body.removeChild(previousButton);
  });

  it("Esc key does NOT dismiss the overlay (informational, not modal)", () => {
    const onRegenerate = vi.fn();
    render(<StaleRunOverlay status="invalidated" onRegenerate={onRegenerate} isPending={false} />);
    const dialog = screen.getByRole("alertdialog");
    expect(dialog).toBeInTheDocument();

    fireEvent.keyDown(window, { key: "Escape" });

    // Overlay still in DOM
    expect(screen.getByRole("alertdialog")).toBeInTheDocument();
    // No regenerate fired
    expect(onRegenerate).not.toHaveBeenCalled();
  });

  it("Tab key keeps focus on the Regenerate button (focus-trap)", () => {
    render(<StaleRunOverlay status="invalidated" onRegenerate={vi.fn()} isPending={false} />);
    const button = screen.getByRole("button", {
      name: /routes\.goal\.stale_overlay_regenerate/i,
    });
    // Move focus elsewhere first to force the focus-trap path
    button.blur();
    fireEvent.keyDown(window, { key: "Tab" });
    expect(button).toHaveFocus();
  });
});

describe("StaleRunOverlay — Regenerate behavior", () => {
  it("clicking Regenerate fires onRegenerate", () => {
    const onRegenerate = vi.fn();
    render(<StaleRunOverlay status="invalidated" onRegenerate={onRegenerate} isPending={false} />);
    fireEvent.click(
      screen.getByRole("button", { name: /routes\.goal\.stale_overlay_regenerate/i }),
    );
    expect(onRegenerate).toHaveBeenCalledTimes(1);
  });

  it("disables Regenerate while isPending=true and renders 'regenerating' label", () => {
    render(<StaleRunOverlay status="invalidated" onRegenerate={vi.fn()} isPending={true} />);
    const button = screen.getByRole("button", { name: /routes\.goal\.regenerating/i });
    expect(button).toBeDisabled();
  });
});

describe("StaleRunOverlay — copy variants per locked §3.2", () => {
  it("renders 'stale' copy for status='invalidated'", () => {
    render(<StaleRunOverlay status="invalidated" onRegenerate={vi.fn()} isPending={false} />);
    expect(screen.getByText("routes.goal.stale_overlay_title")).toBeInTheDocument();
    expect(screen.getByText("routes.goal.stale_overlay_body")).toBeInTheDocument();
  });

  it("renders 'stale' copy for status='superseded'", () => {
    render(<StaleRunOverlay status="superseded" onRegenerate={vi.fn()} isPending={false} />);
    expect(screen.getByText("routes.goal.stale_overlay_title")).toBeInTheDocument();
    expect(screen.getByText("routes.goal.stale_overlay_body")).toBeInTheDocument();
  });

  it("renders 'declined' copy for status='declined'", () => {
    render(<StaleRunOverlay status="declined" onRegenerate={vi.fn()} isPending={false} />);
    expect(screen.getByText("routes.goal.declined_overlay_title")).toBeInTheDocument();
    expect(screen.getByText("routes.goal.declined_overlay_body")).toBeInTheDocument();
    // Stale copy NOT shown
    expect(screen.queryByText("routes.goal.stale_overlay_title")).not.toBeInTheDocument();
  });
});
