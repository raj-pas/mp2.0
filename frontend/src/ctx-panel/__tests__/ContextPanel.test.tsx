/**
 * ContextPanel — P3.2 controlled-Tabs unit tests (plan v20 §A1.32).
 *
 * Verifies:
 *   1. Per-kind render — household / account / goal each show their
 *      tab triggers + initial active panel content.
 *   2. Tab clicking — clicking a non-default trigger swaps the active
 *      panel and persists the choice to localStorage (per-kind key).
 *   3. Reload preservation — pre-seeded localStorage drives the
 *      initial active tab on mount.
 *   4. Empty-state grace — ContextPanel still renders the tab chrome
 *      when the underlying data hook returns no data (§A1.54).
 *
 * useTranslation is mocked globally in test/setup.ts to identity-key,
 * so tab labels render as their i18n keys (e.g. "ctx.tabs.overview").
 *
 * Each test mounts a real Radix Tabs tree wired to the real
 * useLocalStorage hook so the persistence path is exercised end-to-end
 * (no mocking of localStorage).
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { mockAccount, mockGoal, mockHousehold } from "../../__tests__/__fixtures__/household";

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
  useRememberedClientId: () => ["hh_ctx_test", () => {}],
}));

type OverrideRow = {
  id: number;
  score_1_5: number;
  descriptor: string;
  rationale: string;
  created_by: string;
  created_at: string;
};
type OverrideHistoryResult = {
  isPending: boolean;
  isError: boolean;
  data: OverrideRow[] | undefined;
};
const useOverrideHistoryMock = vi.fn<() => OverrideHistoryResult>(() => ({
  isPending: false,
  isError: false,
  data: [],
}));
vi.mock("../../lib/preview", () => ({
  useOverrideHistory: () => useOverrideHistoryMock(),
}));

vi.mock("../../lib/realignment", () => ({
  useSnapshots: () => ({ isPending: false, isError: false, data: [] }),
  useRestoreSnapshot: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock("../../modals/CompareScreen", () => ({
  CompareScreen: () => null,
}));

vi.mock("../../lib/toast", () => ({
  toastError: vi.fn(),
  toastSuccess: vi.fn(),
}));

import { ContextPanel } from "../ContextPanel";

const HOUSEHOLD = mockHousehold({
  goals: [
    mockGoal({ id: "goal_alpha", name: "Retirement" }),
  ],
  accounts: [
    mockAccount({ id: "acct_alpha", type: "RRSP" }),
  ],
});

function renderHousehold() {
  return render(
    <MemoryRouter>
      <ContextPanel kind="household" breadcrumb={["Sandra & Mike Chen"]} />
    </MemoryRouter>,
  );
}

function renderAccount() {
  return render(
    <MemoryRouter initialEntries={["/clients/hh/account/acct_alpha"]}>
      <Routes>
        <Route
          path="/clients/:clientId/account/:accountId"
          element={
            <ContextPanel kind="account" breadcrumb={["Sandra & Mike Chen", "RRSP"]} />
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}

function renderGoal() {
  return render(
    <MemoryRouter initialEntries={["/clients/hh/goal/goal_alpha"]}>
      <Routes>
        <Route
          path="/clients/:clientId/goal/:goalId"
          element={
            <ContextPanel kind="goal" breadcrumb={["Sandra & Mike Chen", "Retirement"]} />
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}

/**
 * Radix Tabs activates a trigger via pointerDown (not click) — see
 * @radix-ui/react-tabs's createTabsScope. fireEvent.click alone is a
 * no-op for trigger activation, so we synthesize the full
 * pointerDown → mouseDown → click sequence the way userEvent would.
 */
function activateTab(el: HTMLElement) {
  fireEvent.pointerDown(el);
  fireEvent.mouseDown(el);
  fireEvent.click(el);
}

/**
 * Sync the lib/local-storage module cache with the current backing
 * window.localStorage by dispatching synthetic StorageEvents. The
 * module subscribes to `storage` events on `window` per active
 * listener and updates its in-memory cache from `event.newValue`.
 * For tests, we still need to evict cache entries even if no React
 * tree is mounted, so we directly call `localStorage.setItem` /
 * `removeItem` (which the cache would re-read on the next React
 * mount because we also clear it via dispatchEvent below).
 *
 * The simplest reliable reset is: clear the localStorage backing,
 * THEN nudge the cache via setItem-removeItem cycles so that any
 * subsequent useLocalStorage() call reads the current empty value.
 */
const KNOWN_CTX_KEYS = [
  "mp20_ctx_panel_collapsed",
  "mp20_ctx_tab_household",
  "mp20_ctx_tab_account",
  "mp20_ctx_tab_goal",
];

function resetCtxLocalStorage() {
  for (const key of KNOWN_CTX_KEYS) {
    window.localStorage.removeItem(key);
  }
  // Force the module-level cache in lib/local-storage to forget any
  // stale entries from prior tests by dispatching a storage event for
  // each known key. The hook's cross-tab `storage` listener picks up
  // event.newValue=null and updates the cache.
  for (const key of KNOWN_CTX_KEYS) {
    window.dispatchEvent(
      new StorageEvent("storage", {
        key,
        newValue: null,
        storageArea: window.localStorage,
      }),
    );
  }
}

beforeEach(() => {
  // Fresh localStorage + module-cache reset per test so persistence
  // assertions are isolated.
  resetCtxLocalStorage();
  useHouseholdMock.mockReturnValue({
    isPending: false,
    isError: false,
    data: HOUSEHOLD,
  });
  useOverrideHistoryMock.mockReturnValue({
    isPending: false,
    isError: false,
    data: [],
  });
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("ContextPanel — household kind", () => {
  it("renders all household tab triggers and the overview panel by default", () => {
    renderHousehold();
    // 4 trigger labels for the household kind.
    expect(screen.getByRole("tab", { name: "ctx.tabs.overview" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "ctx.tabs.allocation" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "ctx.tabs.projections" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "ctx.tabs.history" })).toBeInTheDocument();
    // Overview content is visible — section label drawn from the i18n
    // identity-mock so this matches the key string.
    expect(screen.getByText("ctx.section.household")).toBeInTheDocument();
  });

  it("clicking the projections tab swaps content and writes localStorage", () => {
    renderHousehold();
    activateTab(screen.getByRole("tab", { name: "ctx.tabs.projections" }));
    // Projections tab body shows the deferred-projections empty copy.
    expect(screen.getByText("ctx.deferred.projections_r4")).toBeInTheDocument();
    // Per-kind localStorage key was written with the new active value.
    expect(window.localStorage.getItem("mp20_ctx_tab_household")).toBe(
      JSON.stringify("projections"),
    );
  });
});

describe("ContextPanel — account kind", () => {
  it("renders the account tab triggers (overview / allocation / goals)", () => {
    renderAccount();
    expect(screen.getByRole("tab", { name: "ctx.tabs.overview" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "ctx.tabs.allocation" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "ctx.tabs.goals" })).toBeInTheDocument();
    // Account-overview body shows the regulatory-section labels.
    expect(screen.getByText("ctx.section.account")).toBeInTheDocument();
  });
});

describe("ContextPanel — goal kind", () => {
  it("clicking a tab persists per-kind localStorage independently", () => {
    renderGoal();
    activateTab(screen.getByRole("tab", { name: "ctx.tabs.allocation" }));
    expect(window.localStorage.getItem("mp20_ctx_tab_goal")).toBe(
      JSON.stringify("allocation"),
    );
    // Independence: goal-key write does NOT touch the household/account
    // keys.
    expect(window.localStorage.getItem("mp20_ctx_tab_household")).toBeNull();
    expect(window.localStorage.getItem("mp20_ctx_tab_account")).toBeNull();
  });
});

describe("ContextPanel — reload preservation", () => {
  it("respects pre-seeded localStorage on first render", async () => {
    // Reset Vite's module cache so the lib/local-storage process-wide
    // cache map starts empty. Re-import ContextPanel + helpers from the
    // freshly-loaded module graph so they bind to the pristine hook.
    vi.resetModules();
    window.localStorage.setItem(
      "mp20_ctx_tab_household",
      JSON.stringify("history"),
    );
    const { ContextPanel: FreshContextPanel } = await import("../ContextPanel");
    render(
      <MemoryRouter>
        <FreshContextPanel
          kind="household"
          breadcrumb={["Sandra & Mike Chen"]}
        />
      </MemoryRouter>,
    );
    const historyTab = screen.getByRole("tab", { name: "ctx.tabs.history" });
    expect(historyTab).toHaveAttribute("data-state", "active");
  });
});

describe("ContextPanel — empty state (§A1.54)", () => {
  it("renders the tab chrome even when the underlying household data is missing", () => {
    useHouseholdMock.mockReturnValue({
      isPending: false,
      isError: false,
      data: undefined,
    });
    renderHousehold();
    // Tab triggers still render so the user can navigate.
    expect(screen.getByRole("tab", { name: "ctx.tabs.overview" })).toBeInTheDocument();
    // The body falls back to the missing-client copy.
    expect(screen.getByText("routes.household.missing_client")).toBeInTheDocument();
  });
});

describe("ContextPanel — collapsed mode", () => {
  it("renders the slim collapsed rail when the panel is collapsed", async () => {
    // Pre-seed `mp20_ctx_panel_collapsed=true` and re-import via fresh
    // module graph so the lib/local-storage cache reads the new value.
    vi.resetModules();
    window.localStorage.setItem("mp20_ctx_panel_collapsed", JSON.stringify(true));
    const { ContextPanel: FreshContextPanel } = await import("../ContextPanel");
    render(
      <MemoryRouter>
        <FreshContextPanel kind="household" breadcrumb={["Sandra & Mike Chen"]} />
      </MemoryRouter>,
    );
    // Collapsed rail surfaces only the Expand button — no tab triggers.
    expect(
      screen.getByRole("button", { name: "ctx.expand" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "ctx.tabs.overview" })).toBeNull();
  });

  it("clicking the expand button re-renders the full tab chrome", async () => {
    vi.resetModules();
    window.localStorage.setItem("mp20_ctx_panel_collapsed", JSON.stringify(true));
    const { ContextPanel: FreshContextPanel } = await import("../ContextPanel");
    render(
      <MemoryRouter>
        <FreshContextPanel kind="household" breadcrumb={["Sandra & Mike Chen"]} />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "ctx.expand" }));
    expect(
      screen.getByRole("tab", { name: "ctx.tabs.overview" }),
    ).toBeInTheDocument();
    // Collapse button now visible (paired affordance).
    expect(
      screen.getByRole("button", { name: "ctx.collapse" }),
    ).toBeInTheDocument();
  });
});

describe("ContextPanel — household allocation tab body", () => {
  it("renders the fund-mix stack on the allocation tab when holdings exist", () => {
    renderHousehold();
    activateTab(screen.getByRole("tab", { name: "ctx.tabs.allocation" }));
    // Fund-mix section label and at least one holding name from the
    // mockAccount fixture (SH Equity / SH Income / SH Savings).
    expect(screen.getByText("ctx.section.fund_mix")).toBeInTheDocument();
    expect(screen.getByText("SH Income")).toBeInTheDocument();
  });

  it("renders the no-holdings empty state when fund-mix total is zero", () => {
    useHouseholdMock.mockReturnValue({
      isPending: false,
      isError: false,
      data: mockHousehold({ accounts: [mockAccount({ holdings: [] })] }),
    });
    renderHousehold();
    activateTab(screen.getByRole("tab", { name: "ctx.tabs.allocation" }));
    expect(screen.getByText("ctx.deferred.no_holdings")).toBeInTheDocument();
  });
});

describe("ContextPanel — goal context tab body", () => {
  it("renders the override-history empty state on the projections tab", () => {
    renderGoal();
    activateTab(screen.getByRole("tab", { name: "ctx.tabs.projections" }));
    // GoalContext's projections tab body uses risk_slider.history_title +
    // history_empty when overrides are empty.
    expect(screen.getByText("risk_slider.history_title")).toBeInTheDocument();
    expect(screen.getByText("risk_slider.history_empty")).toBeInTheDocument();
  });

  it("renders override-history rows when present", () => {
    useOverrideHistoryMock.mockReturnValue({
      isPending: false,
      isError: false,
      data: [
        {
          id: 1,
          score_1_5: 3,
          descriptor: "Balanced",
          rationale: "Client wants moderate risk",
          created_by: "advisor@example.com",
          created_at: "2026-05-01T00:00:00Z",
        },
      ],
    });
    renderGoal();
    activateTab(screen.getByRole("tab", { name: "ctx.tabs.projections" }));
    expect(screen.getByText("risk_slider.history_score")).toBeInTheDocument();
    expect(screen.getByText("Client wants moderate risk")).toBeInTheDocument();
  });

  it("renders the override-history error fallback", () => {
    useOverrideHistoryMock.mockReturnValue({
      isPending: false,
      isError: true,
      data: undefined,
    });
    renderGoal();
    activateTab(screen.getByRole("tab", { name: "ctx.tabs.projections" }));
    expect(screen.getByText("errors.preview_failed")).toBeInTheDocument();
  });

  it("shows the override-history skeleton when the query is pending", () => {
    useOverrideHistoryMock.mockReturnValue({
      isPending: true,
      isError: false,
      data: undefined,
    });
    const { container } = renderGoal();
    activateTab(screen.getByRole("tab", { name: "ctx.tabs.projections" }));
    // Skeleton is rendered as a div with role/data-state markers; just
    // assert the projections-tab section label is visible to confirm
    // we hit the loading branch (no error / no rows / no empty copy).
    expect(screen.queryByText("risk_slider.history_empty")).toBeNull();
    expect(container.querySelector(".animate-pulse")).toBeTruthy();
  });

  it("renders linked-account allocation rows on the allocation tab", () => {
    useHouseholdMock.mockReturnValue({
      isPending: false,
      isError: false,
      data: mockHousehold({
        goals: [
          mockGoal({
            id: "goal_alpha",
            name: "Retirement",
            account_allocations: [
              {
                id: "link_a",
                goal_id: "goal_alpha",
                account_id: "acct_alpha",
                allocated_amount: 30000,
                allocated_pct: null,
              },
            ],
          }),
        ],
      }),
    });
    renderGoal();
    activateTab(screen.getByRole("tab", { name: "ctx.tabs.allocation" }));
    expect(screen.getByText("routes.goal.linked_accounts_title")).toBeInTheDocument();
    expect(screen.getByText("acct_alpha")).toBeInTheDocument();
  });

  it("renders the linked-accounts empty state when no allocations exist", () => {
    useHouseholdMock.mockReturnValue({
      isPending: false,
      isError: false,
      data: mockHousehold({
        goals: [
          mockGoal({
            id: "goal_alpha",
            name: "Retirement",
            account_allocations: [],
          }),
        ],
      }),
    });
    renderGoal();
    activateTab(screen.getByRole("tab", { name: "ctx.tabs.allocation" }));
    expect(screen.getByText("empty.no_holdings")).toBeInTheDocument();
  });

  it("renders the missing-goal fallback when the route param has no match", () => {
    render(
      <MemoryRouter initialEntries={["/clients/hh/goal/goal_unknown"]}>
        <Routes>
          <Route
            path="/clients/:clientId/goal/:goalId"
            element={
              <ContextPanel
                kind="goal"
                breadcrumb={["Sandra & Mike Chen", "Unknown"]}
              />
            }
          />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByText("routes.goal.missing_goal")).toBeInTheDocument();
  });
});

describe("ContextPanel — account context tab body", () => {
  it("renders the goals-in-account empty state when no allocations exist", () => {
    // Override the mocked household so the account has zero linked goals.
    useHouseholdMock.mockReturnValue({
      isPending: false,
      isError: false,
      data: mockHousehold({
        goals: [],
        accounts: [mockAccount({ id: "acct_alpha", type: "RRSP" })],
      }),
    });
    renderAccount();
    activateTab(screen.getByRole("tab", { name: "ctx.tabs.goals" }));
    expect(screen.getByText("routes.account.no_goals_in_account")).toBeInTheDocument();
  });

  it("lists each goal allocated to the account on the goals tab", () => {
    useHouseholdMock.mockReturnValue({
      isPending: false,
      isError: false,
      data: mockHousehold({
        goals: [
          mockGoal({
            id: "goal_alpha",
            name: "Retirement",
            account_allocations: [
              {
                id: "link_a",
                goal_id: "goal_alpha",
                account_id: "acct_alpha",
                allocated_amount: 25000,
                allocated_pct: null,
              },
            ],
          }),
        ],
        accounts: [mockAccount({ id: "acct_alpha", type: "RRSP", holdings: [] })],
      }),
    });
    renderAccount();
    activateTab(screen.getByRole("tab", { name: "ctx.tabs.goals" }));
    expect(screen.getByText("Retirement")).toBeInTheDocument();
  });

  it("renders the top-funds list on the allocation tab when holdings exist", () => {
    renderAccount();
    activateTab(screen.getByRole("tab", { name: "ctx.tabs.allocation" }));
    expect(screen.getByText("routes.account.top_funds_title")).toBeInTheDocument();
    expect(screen.getByText("SH Income")).toBeInTheDocument();
  });

  it("renders no-holdings empty state when the account has no holdings", () => {
    useHouseholdMock.mockReturnValue({
      isPending: false,
      isError: false,
      data: mockHousehold({
        accounts: [mockAccount({ id: "acct_alpha", holdings: [] })],
      }),
    });
    renderAccount();
    activateTab(screen.getByRole("tab", { name: "ctx.tabs.allocation" }));
    expect(screen.getByText("routes.account.no_holdings")).toBeInTheDocument();
  });

  it("renders the missing-account fallback when the route param has no match", () => {
    // Render with a route that has no matching account id in the
    // household fixture.
    render(
      <MemoryRouter initialEntries={["/clients/hh/account/acct_unknown"]}>
        <Routes>
          <Route
            path="/clients/:clientId/account/:accountId"
            element={
              <ContextPanel
                kind="account"
                breadcrumb={["Sandra & Mike Chen", "Unknown"]}
              />
            }
          />
        </Routes>
      </MemoryRouter>,
    );
    // Body falls back to the missing-account copy; tab triggers still
    // render so the user can navigate away.
    expect(screen.getByText("routes.account.missing_account")).toBeInTheDocument();
  });
});

describe("ContextPanel — defensive fallback", () => {
  it("falls back to the first tab when persisted value is no longer in the catalog", async () => {
    // Seed a stale value that was valid for "household" but not for
    // "account" (mismatch e.g. catalog change between releases).
    vi.resetModules();
    window.localStorage.setItem("mp20_ctx_tab_account", JSON.stringify("history"));
    const { ContextPanel: FreshContextPanel } = await import("../ContextPanel");
    render(
      <MemoryRouter initialEntries={["/clients/hh/account/acct_alpha"]}>
        <Routes>
          <Route
            path="/clients/:clientId/account/:accountId"
            element={
              <FreshContextPanel
                kind="account"
                breadcrumb={["Sandra & Mike Chen", "RRSP"]}
              />
            }
          />
        </Routes>
      </MemoryRouter>,
    );
    // Account kind has no "history" tab — the panel falls back to
    // "overview" rather than rendering an unknown active value.
    const overview = screen.getByRole("tab", { name: "ctx.tabs.overview" });
    expect(overview).toHaveAttribute("data-state", "active");
  });
});
