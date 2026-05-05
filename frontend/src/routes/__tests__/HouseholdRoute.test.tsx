/**
 * HouseholdRoute — P11 structural tests (plan v20 §A1.27 + §A1.18 LOCKED layout).
 *
 * Verifies the UnallocatedBanner placeholder slot sits ABOVE the
 * action sub-bar / HouseholdPortfolioPanel per the locked layout. The
 * full UnallocatedBanner component lands in P12 (next pair) — these
 * tests target the structural slot only.
 */
import React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { mockHousehold } from "../../__tests__/__fixtures__/household";

const useHouseholdMock = vi.fn();
vi.mock("../../lib/household", async () => {
  const actual = await vi.importActual<typeof import("../../lib/household")>(
    "../../lib/household",
  );
  return {
    ...actual,
    useHousehold: () => useHouseholdMock(),
  };
});

vi.mock("../../chrome/ClientPicker", () => ({
  useRememberedClientId: () => ["hh_test_p11", () => {}],
}));

vi.mock("../../lib/treemap", () => ({
  useTreemap: () => ({ isPending: false, isError: false, isSuccess: false }),
}));

vi.mock("../../lib/preview", () => ({
  useGeneratePortfolio: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock("../../lib/realignment", () => ({
  useRestoreSnapshot: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock("../../lib/toast", () => ({
  toastError: vi.fn(),
  toastSuccess: vi.fn(),
}));

vi.mock("../../modals/RealignModal", () => ({
  RealignModal: () => null,
}));

vi.mock("../../modals/CompareScreen", () => ({
  CompareScreen: () => null,
}));

vi.mock("../../treemap/Treemap", () => ({
  Treemap: () => null,
}));

import { HouseholdRoute } from "../HouseholdRoute";

function renderRoute() {
  return render(
    <MemoryRouter>
      <HouseholdRoute />
    </MemoryRouter>,
  );
}

describe("HouseholdRoute — UnallocatedBanner placeholder slot (§A1.18 LOCKED)", () => {
  it("renders the unallocated-banner-slot placeholder when household loads", () => {
    useHouseholdMock.mockReturnValue({
      isPending: false,
      isError: false,
      data: mockHousehold(),
    });
    renderRoute();
    expect(screen.getByTestId("unallocated-banner-slot")).toBeInTheDocument();
  });

  it("placeholder slot has aria-label for assistive tech (sister §A11y)", () => {
    useHouseholdMock.mockReturnValue({
      isPending: false,
      isError: false,
      data: mockHousehold(),
    });
    renderRoute();
    expect(screen.getByTestId("unallocated-banner-slot")).toHaveAttribute(
      "aria-label",
      "routes.household.unallocated_banner_slot_aria",
    );
  });

  it("slot sits above HouseholdPortfolioPanel in DOM order (§A1.18 layout)", () => {
    useHouseholdMock.mockReturnValue({
      isPending: false,
      isError: false,
      data: mockHousehold({
        latest_portfolio_run: null,
        latest_portfolio_failure: null,
      }),
    });
    const { container } = renderRoute();
    const slot = container.querySelector('[data-testid="unallocated-banner-slot"]');
    const panel = container.querySelector(
      'section[aria-labelledby^="household-portfolio-"]',
    );
    expect(slot).toBeTruthy();
    expect(panel).toBeTruthy();
    // DOM-order: slot must come BEFORE the portfolio panel.
    if (slot && panel) {
      const position = slot.compareDocumentPosition(panel);
      // Node.DOCUMENT_POSITION_FOLLOWING = 4 means panel comes after slot.
      expect(position & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    }
  });
});
