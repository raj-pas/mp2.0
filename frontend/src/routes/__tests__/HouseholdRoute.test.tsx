/**
 * HouseholdRoute — P11 + P12 + P2.1/P2.5 structural tests (plan v20
 * §A1.27 + §A1.18 LOCKED layout + §A1.30).
 *
 * P11 introduced the unallocated-banner placeholder slot ABOVE the
 * action sub-bar / HouseholdPortfolioPanel. P12 (this pair) replaced
 * the placeholder with the actual ``<UnallocatedBanner>`` component.
 * P2.1 + P2.5 added Re-open + Re-reconcile CTAs to the action sub-bar.
 * The placeholder div is retained as a hidden no-op for downstream
 * structural assertions (§A1.51 cross-phase coexistence).
 */
import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type * as HouseholdLibModule from "../../lib/household";
import type * as ClientsLibModule from "../../lib/clients";
import type * as ReactRouterDomModule from "react-router-dom";
import { mockHousehold } from "../../__tests__/__fixtures__/household";

const useHouseholdMock = vi.fn();
vi.mock("../../lib/household", async () => {
  const actual = await vi.importActual<typeof HouseholdLibModule>("../../lib/household");
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

const reopenMutateMock = vi.fn();
const reconcileMutateMock = vi.fn();
const useReopenMock = vi.fn();
const useReconcileMock = vi.fn();
vi.mock("../../lib/clients", async () => {
  const actual = await vi.importActual<typeof ClientsLibModule>("../../lib/clients");
  return {
    ...actual,
    useReopenHousehold: () => useReopenMock(),
    useReconcileHousehold: () => useReconcileMock(),
  };
});

const navigateMock = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof ReactRouterDomModule>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

const toastErrorMock = vi.fn();
const toastSuccessMock = vi.fn();
vi.mock("../../lib/toast", () => ({
  toastError: (...args: unknown[]) => toastErrorMock(...args),
  toastSuccess: (...args: unknown[]) => toastSuccessMock(...args),
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

function resetMutationMocks() {
  reopenMutateMock.mockReset();
  reconcileMutateMock.mockReset();
  navigateMock.mockReset();
  toastErrorMock.mockReset();
  toastSuccessMock.mockReset();
  useReopenMock.mockReturnValue({ mutate: reopenMutateMock, isPending: false });
  useReconcileMock.mockReturnValue({
    mutate: reconcileMutateMock,
    isPending: false,
  });
}

describe("HouseholdRoute — UnallocatedBanner placeholder slot (§A1.18 LOCKED)", () => {
  beforeEach(() => {
    resetMutationMocks();
  });

  it("renders the unallocated-banner-slot placeholder when household loads", () => {
    useHouseholdMock.mockReturnValue({
      isPending: false,
      isError: false,
      data: mockHousehold(),
    });
    renderRoute();
    expect(screen.getByTestId("unallocated-banner-slot")).toBeInTheDocument();
  });

  it("placeholder slot is hidden after P12 mounts the real UnallocatedBanner", () => {
    // P12 replaces the placeholder rendering with the actual
    // UnallocatedBanner. The placeholder div is retained but hidden so
    // structural assertions targeting the test-id continue to pass
    // (§A1.51 — backwards-compat).
    useHouseholdMock.mockReturnValue({
      isPending: false,
      isError: false,
      data: mockHousehold(),
    });
    renderRoute();
    const slot = screen.getByTestId("unallocated-banner-slot");
    expect(slot).toHaveAttribute("aria-hidden", "true");
    expect(slot).toHaveAttribute("hidden");
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

describe("HouseholdRoute — Re-open / Re-reconcile sub-bar CTAs (§A1.30)", () => {
  beforeEach(() => {
    resetMutationMocks();
    useHouseholdMock.mockReturnValue({
      isPending: false,
      isError: false,
      data: mockHousehold(),
    });
  });

  it("renders both Re-open and Re-reconcile buttons in the action sub-bar", () => {
    renderRoute();
    expect(screen.getByTestId("household-reopen-button")).toBeInTheDocument();
    expect(screen.getByTestId("household-reconcile-button")).toBeInTheDocument();
  });

  it("disables both CTAs while a reopen mutation is in flight", () => {
    useReopenMock.mockReturnValue({ mutate: reopenMutateMock, isPending: true });
    useReconcileMock.mockReturnValue({
      mutate: reconcileMutateMock,
      isPending: false,
    });
    renderRoute();
    expect(screen.getByTestId("household-reopen-button")).toBeDisabled();
    expect(screen.getByTestId("household-reconcile-button")).toBeDisabled();
  });

  it("Re-open click navigates to /review/<wsid> on success", async () => {
    reopenMutateMock.mockImplementation((_, opts) => {
      opts?.onSuccess?.({
        workspace: { external_id: "ws_reopen_42" },
        redirect_url: "/review/ws_reopen_42",
      });
    });
    renderRoute();
    fireEvent.click(screen.getByTestId("household-reopen-button"));
    await waitFor(() => {
      expect(navigateMock).toHaveBeenCalledWith("/review/ws_reopen_42");
    });
  });

  it("Re-reconcile noop response shows success toast and stays on route", async () => {
    reconcileMutateMock.mockImplementation((_, opts) => {
      opts?.onSuccess?.({ noop: true, redirect_url: null });
    });
    renderRoute();
    fireEvent.click(screen.getByTestId("household-reconcile-button"));
    await waitFor(() => {
      expect(toastSuccessMock).toHaveBeenCalled();
    });
    expect(navigateMock).not.toHaveBeenCalled();
  });

  it("Re-open error fires toast with structured copy", async () => {
    reopenMutateMock.mockImplementation((_, opts) => {
      opts?.onError?.(new Error("boom"));
    });
    renderRoute();
    fireEvent.click(screen.getByTestId("household-reopen-button"));
    await waitFor(() => {
      expect(toastErrorMock).toHaveBeenCalled();
    });
  });
});
