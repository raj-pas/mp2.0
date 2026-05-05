/**
 * IntegrityAlertOverlay — engineering-only overlay (Phase A4 / locked §3.2).
 *
 * No focus management, no Regenerate button, no advisor action; backend
 * audit emission already shipped in Phase A1 (web/api/serializers.py:298-340).
 */
import React from "react";
import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import { IntegrityAlertOverlay } from "../IntegrityAlertOverlay";

describe("IntegrityAlertOverlay — engineering-only contract", () => {
  it("renders with role='alert'", () => {
    render(<IntegrityAlertOverlay runSignature="abc12345" />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("does NOT render a Regenerate button (advisor-not-actionable)", () => {
    render(<IntegrityAlertOverlay runSignature="abc12345" />);
    expect(
      screen.queryByRole("button", { name: /regenerate/i }),
    ).not.toBeInTheDocument();
  });

  it("renders the run signature reference (8-char prefix)", () => {
    render(<IntegrityAlertOverlay runSignature="abcdef1234567890" />);
    // i18n stub returns the key; the interpolated signature is in the options arg.
    // The signature line uses the run_ref key.
    expect(
      screen.getByText("routes.goal.integrity_overlay_run_ref"),
    ).toBeInTheDocument();
  });

  it("hides signature reference when runSignature is null/empty", () => {
    render(<IntegrityAlertOverlay runSignature={null} />);
    expect(
      screen.queryByText("routes.goal.integrity_overlay_run_ref"),
    ).not.toBeInTheDocument();
  });

  it("Esc key does NOT dismiss (informational only)", () => {
    render(<IntegrityAlertOverlay runSignature="abc12345" />);
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("ARIA: aria-labelledby + aria-describedby resolve to translated text nodes", () => {
    render(<IntegrityAlertOverlay runSignature="abc12345" />);
    const alert = screen.getByRole("alert");
    expect(alert).toHaveAttribute("aria-labelledby", "integrity-overlay-title");
    expect(alert).toHaveAttribute("aria-describedby", "integrity-overlay-body");
    expect(screen.getByText("routes.goal.integrity_overlay_title")).toBeInTheDocument();
    expect(screen.getByText("routes.goal.integrity_overlay_body")).toBeInTheDocument();
  });

  it("StrictMode double-invoke does not throw (locked #64)", () => {
    expect(() => {
      render(
        <React.StrictMode>
          <IntegrityAlertOverlay runSignature="abc12345" />
        </React.StrictMode>,
      );
    }).not.toThrow();
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});
