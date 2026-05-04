/**
 * SourcePill — engine vs calibration vs calibration_drag visual indicator.
 *
 * Per locked decisions §3.1, §3.3, §3.4, §3.7.
 *
 * Note: react-i18next is mocked in `src/test/setup.ts` to return the key
 * itself; tests assert on the i18n key, not the resolved English copy.
 */
import React from "react";
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { SourcePill } from "../SourcePill";

describe("SourcePill", () => {
  it("renders engine variant with run-signature 8-char prefix when source='engine'", () => {
    render(<SourcePill source="engine" runSignature="abc123def456ghi789" />);
    expect(screen.getByText("goal_allocation.from_run")).toBeInTheDocument();
    // 8-char prefix shown
    expect(screen.getByText(/abc123de/)).toBeInTheDocument();
    // Full 18-char signature NOT shown (only 8-char prefix)
    expect(screen.queryByText("abc123def456ghi789")).not.toBeInTheDocument();
  });

  it("renders engine variant without signature suffix when runSignature is null", () => {
    render(<SourcePill source="engine" runSignature={null} />);
    expect(screen.getByText("goal_allocation.from_run")).toBeInTheDocument();
    // No "·" separator when no signature
    expect(screen.queryByText(/·/)).not.toBeInTheDocument();
  });

  it("renders calibration variant when source='calibration'", () => {
    render(<SourcePill source="calibration" />);
    expect(screen.getByText("goal_allocation.from_calibration")).toBeInTheDocument();
  });

  it("renders calibration_drag variant with distinct copy when source='calibration_drag'", () => {
    render(<SourcePill source="calibration_drag" />);
    expect(screen.getByText("goal_allocation.from_calibration_drag")).toBeInTheDocument();
    // Engine variant copy NOT shown
    expect(screen.queryByText("goal_allocation.from_run")).not.toBeInTheDocument();
  });

  it("uses role='status' + aria-label for SR-friendliness (WCAG 4.1.3)", () => {
    render(<SourcePill source="engine" runSignature="abc12345" />);
    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-label", "goal_allocation.from_run");
    // Signature is aria-hidden so SR doesn't read out the hex string.
    const sig = status.querySelector("span[aria-hidden='true']");
    expect(sig).not.toBeNull();
  });
});
