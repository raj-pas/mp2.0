/**
 * ToggleCurrentIdeal — P7 (plan v20 §A1.35 / G9) unit tests.
 *
 * Coverage (4 cases):
 *   1. Renders both options + role="group" wrapper (default state).
 *   2. Disabled-when-no-PortfolioRun coerces value to "current" + adds
 *      aria-disabled to the "Ideal" option.
 *   3. Click flips persisted value (state change).
 *   4. localStorage write under the §A1.14 #14 per-user global key.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  ToggleCurrentIdeal,
  STORAGE_CURRENT_IDEAL,
} from "../ToggleCurrentIdeal";

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  window.localStorage.clear();
});

describe("ToggleCurrentIdeal — P7 / §A1.35", () => {
  it("renders both options inside a labeled role=group wrapper", () => {
    render(<ToggleCurrentIdeal />);
    const group = screen.getByRole("group", {
      name: "toggle.current_ideal.aria_label",
    });
    expect(group).toBeInTheDocument();
    expect(
      screen.getByTestId("toggle-current-ideal-current"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("toggle-current-ideal-ideal"),
    ).toBeInTheDocument();
    // Default value is "current" → aria-pressed=true on that button.
    expect(
      screen.getByTestId("toggle-current-ideal-current"),
    ).toHaveAttribute("aria-pressed", "true");
  });

  it("disabled=true coerces value to 'current' + sets aria-disabled on 'Ideal'", () => {
    // Pre-seed localStorage to "ideal" — the disabled-mode coercion
    // must override the persisted value at the render layer.
    window.localStorage.setItem(STORAGE_CURRENT_IDEAL, JSON.stringify("ideal"));
    render(<ToggleCurrentIdeal disabled />);
    // Even though localStorage says "ideal", the render must show
    // "current" as pressed (per §A1.35 disabled-coercion contract).
    expect(
      screen.getByTestId("toggle-current-ideal-current"),
    ).toHaveAttribute("aria-pressed", "true");
    // The "Ideal" button is aria-disabled + native disabled.
    const idealBtn = screen.getByTestId("toggle-current-ideal-ideal");
    expect(idealBtn).toHaveAttribute("aria-disabled", "true");
    expect(idealBtn).toBeDisabled();
  });

  it("clicking 'ideal' flips aria-pressed (state change)", () => {
    render(<ToggleCurrentIdeal />);
    const idealBtn = screen.getByTestId("toggle-current-ideal-ideal");
    fireEvent.click(idealBtn);
    expect(idealBtn).toHaveAttribute("aria-pressed", "true");
    expect(
      screen.getByTestId("toggle-current-ideal-current"),
    ).toHaveAttribute("aria-pressed", "false");
  });

  it("writes to localStorage under the §A1.14 #14 per-user global key", () => {
    render(<ToggleCurrentIdeal />);
    fireEvent.click(screen.getByTestId("toggle-current-ideal-ideal"));
    expect(window.localStorage.getItem(STORAGE_CURRENT_IDEAL)).toBe(
      JSON.stringify("ideal"),
    );
    fireEvent.click(screen.getByTestId("toggle-current-ideal-current"));
    expect(window.localStorage.getItem(STORAGE_CURRENT_IDEAL)).toBe(
      JSON.stringify("current"),
    );
  });
});
