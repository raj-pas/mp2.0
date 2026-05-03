/**
 * WelcomeTour — first-login coachmark unit tests (Phase 6 sub-session #4).
 *
 * Verifies:
 *   - hidden when `tour_completed_at` is set, shown otherwise
 *   - 3-step navigation via Next button
 *   - Done + Skip both call useCompleteTour.mutate (idempotent server ack)
 */
import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { WelcomeTour } from "../WelcomeTour";
import type { SessionUser } from "../../lib/auth";

const completeMutate = vi.fn();

vi.mock("../../lib/auth", () => ({
  useCompleteTour: () => ({
    mutate: completeMutate,
    isPending: false,
  }),
}));

function makeUser(overrides: Partial<SessionUser> = {}): SessionUser {
  return {
    email: "advisor@example.com",
    name: "Advisor",
    role: "advisor",
    team: null,
    engine_enabled: true,
    disclaimer_acknowledged_at: "2026-05-01T00:00:00Z",
    disclaimer_acknowledged_version: "v1",
    tour_completed_at: null,
    ...overrides,
  };
}

afterEach(() => {
  completeMutate.mockClear();
});

describe("WelcomeTour", () => {
  it("renders the dialog when tour_completed_at is null", () => {
    render(<WelcomeTour user={makeUser()} />);
    expect(screen.getByRole("dialog")).toHaveAttribute(
      "aria-label",
      "chrome.welcome_tour.aria_label",
    );
    // Step 1 of 3:
    expect(screen.getByText("1 / 3")).toBeInTheDocument();
    expect(
      screen.getByText("chrome.welcome_tour.step_pick_client_heading"),
    ).toBeInTheDocument();
  });

  it("hides the dialog when tour_completed_at is set", () => {
    const { container } = render(
      <WelcomeTour
        user={makeUser({ tour_completed_at: "2026-05-01T00:00:00Z" })}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("Next advances through 3 steps then commits on Done", () => {
    render(<WelcomeTour user={makeUser()} />);
    // Step 1 -> 2.
    fireEvent.click(
      screen.getByRole("button", { name: "chrome.welcome_tour.next" }),
    );
    expect(screen.getByText("2 / 3")).toBeInTheDocument();
    expect(
      screen.getByText("chrome.welcome_tour.step_drill_treemap_heading"),
    ).toBeInTheDocument();

    // Step 2 -> 3 (last).
    fireEvent.click(
      screen.getByRole("button", { name: "chrome.welcome_tour.next" }),
    );
    expect(screen.getByText("3 / 3")).toBeInTheDocument();
    // The Next button now reads "done".
    const doneButton = screen.getByRole("button", {
      name: "chrome.welcome_tour.done",
    });
    expect(doneButton).toBeInTheDocument();

    // Done -> mutate + close.
    fireEvent.click(doneButton);
    expect(completeMutate).toHaveBeenCalledTimes(1);
  });

  it("Skip calls useCompleteTour.mutate from any step", () => {
    render(<WelcomeTour user={makeUser()} />);
    fireEvent.click(
      screen.getByRole("button", { name: "chrome.welcome_tour.skip" }),
    );
    expect(completeMutate).toHaveBeenCalledTimes(1);
  });

  it("after Skip the dialog is removed from the DOM", () => {
    const { rerender } = render(<WelcomeTour user={makeUser()} />);
    fireEvent.click(
      screen.getByRole("button", { name: "chrome.welcome_tour.skip" }),
    );
    // Manually invoke the onSettled callback the component passed
    // to the mock — that's what flips `closed` and unmounts the dialog.
    const onSettled = completeMutate.mock.calls[0]?.[1]?.onSettled as
      | (() => void)
      | undefined;
    expect(typeof onSettled).toBe("function");
    act(() => {
      onSettled?.();
    });
    rerender(<WelcomeTour user={makeUser()} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
