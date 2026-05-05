/**
 * ToggleFundAssetClass — P6 (plan v20 §A1.35 / G8) unit tests.
 *
 * Coverage (4 cases):
 *   1. Renders both options + role="group" wrapper.
 *   2. Click flips persisted value (state change).
 *   3. localStorage write under the §A1.14 #14 per-user global key.
 *   4. Cross-route persistence — a second mount picks up the prior write.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  ToggleFundAssetClass,
  STORAGE_FUND_ASSET,
} from "../ToggleFundAssetClass";

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  window.localStorage.clear();
});

describe("ToggleFundAssetClass — P6 / §A1.35", () => {
  it("renders both options inside a labeled role=group wrapper", () => {
    render(<ToggleFundAssetClass />);
    const group = screen.getByRole("group", {
      name: "toggle.fund_asset.aria_label",
    });
    expect(group).toBeInTheDocument();
    expect(screen.getByTestId("toggle-fund-asset-fund")).toBeInTheDocument();
    expect(
      screen.getByTestId("toggle-fund-asset-asset_class"),
    ).toBeInTheDocument();
    // Default value is "fund" → aria-pressed=true on that button.
    expect(screen.getByTestId("toggle-fund-asset-fund")).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(
      screen.getByTestId("toggle-fund-asset-asset_class"),
    ).toHaveAttribute("aria-pressed", "false");
  });

  it("clicking 'asset_class' flips aria-pressed (state change)", () => {
    render(<ToggleFundAssetClass />);
    const assetBtn = screen.getByTestId("toggle-fund-asset-asset_class");
    fireEvent.click(assetBtn);
    expect(assetBtn).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("toggle-fund-asset-fund")).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("writes to localStorage under the §A1.14 #14 per-user global key", () => {
    render(<ToggleFundAssetClass />);
    fireEvent.click(screen.getByTestId("toggle-fund-asset-asset_class"));
    expect(window.localStorage.getItem(STORAGE_FUND_ASSET)).toBe(
      JSON.stringify("asset_class"),
    );
    fireEvent.click(screen.getByTestId("toggle-fund-asset-fund"));
    expect(window.localStorage.getItem(STORAGE_FUND_ASSET)).toBe(
      JSON.stringify("fund"),
    );
  });

  it("persists across mounts — second mount inherits prior write (cross-route persistence)", () => {
    // First mount: flip to asset_class.
    const { unmount } = render(<ToggleFundAssetClass />);
    fireEvent.click(screen.getByTestId("toggle-fund-asset-asset_class"));
    unmount();
    // Second mount (simulates landing on the other route): must pick up
    // the prior persisted value without further interaction.
    render(<ToggleFundAssetClass />);
    expect(
      screen.getByTestId("toggle-fund-asset-asset_class"),
    ).toHaveAttribute("aria-pressed", "true");
  });
});
