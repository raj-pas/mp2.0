/**
 * PilotBanner — disclaimer banner unit tests (Phase 6 sub-session #4).
 *
 * Verifies the version-aware show/hide gating + dismiss-mutation wiring.
 * Uses a `vi.mock` factory for `../../lib/auth` so we control both
 * `DISCLAIMER_VERSION` (current canon) and the `useAcknowledgeDisclaimer`
 * hook surface that PilotBanner calls.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PilotBanner } from "../PilotBanner";
import type { SessionUser } from "../../lib/auth";

const ackMutate = vi.fn();
const ackPending = { current: false };

vi.mock("../../lib/auth", () => ({
  DISCLAIMER_VERSION: "v1",
  useAcknowledgeDisclaimer: () => ({
    mutate: ackMutate,
    get isPending() {
      return ackPending.current;
    },
  }),
}));

vi.mock("../../lib/toast", () => ({
  toastError: vi.fn(),
  toastSuccess: vi.fn(),
}));

function makeUser(overrides: Partial<SessionUser> = {}): SessionUser {
  return {
    email: "advisor@example.com",
    name: "Advisor",
    role: "advisor",
    team: null,
    engine_enabled: true,
    disclaimer_acknowledged_at: null,
    disclaimer_acknowledged_version: "",
    tour_completed_at: "2026-04-30T00:00:00Z",
    ...overrides,
  };
}

afterEach(() => {
  ackMutate.mockClear();
  ackPending.current = false;
});

describe("PilotBanner", () => {
  it("renders the banner when the advisor has never acknowledged", () => {
    render(<PilotBanner user={makeUser()} />);
    expect(screen.getByRole("region")).toHaveAttribute(
      "aria-label",
      "chrome.pilot_banner.aria_label",
    );
    expect(screen.getByText("chrome.pilot_banner.title")).toBeInTheDocument();
    expect(screen.getByText("chrome.pilot_banner.dismiss")).toBeInTheDocument();
  });

  it("hides the banner when ack timestamp + version match canon", () => {
    const { container } = render(
      <PilotBanner
        user={makeUser({
          disclaimer_acknowledged_at: "2026-05-01T00:00:00Z",
          disclaimer_acknowledged_version: "v1",
        })}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("re-shows the banner when the advisor acked an older version", () => {
    render(
      <PilotBanner
        user={makeUser({
          disclaimer_acknowledged_at: "2026-04-01T00:00:00Z",
          disclaimer_acknowledged_version: "v0",
        })}
      />,
    );
    expect(screen.getByRole("region")).toBeInTheDocument();
    expect(screen.getByText("chrome.pilot_banner.dismiss")).toBeInTheDocument();
  });

  it("clicking Dismiss calls the ack mutation with the current version", () => {
    render(<PilotBanner user={makeUser()} />);
    fireEvent.click(screen.getByText("chrome.pilot_banner.dismiss"));
    expect(ackMutate).toHaveBeenCalledTimes(1);
    expect(ackMutate.mock.calls[0]?.[0]).toEqual({ version: "v1" });
  });

  it("disables Dismiss while the mutation is pending", () => {
    ackPending.current = true;
    render(<PilotBanner user={makeUser()} />);
    const dismiss = screen.getByText("chrome.pilot_banner.dismiss_pending");
    expect(dismiss.closest("button")).toBeDisabled();
  });
});
