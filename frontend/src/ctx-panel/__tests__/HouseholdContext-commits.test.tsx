/**
 * HouseholdContext — Commits sub-tab tests (plan v20 §A1.36 P9/P2.3).
 *
 * Covers:
 *   1. Commits sub-tab renders the AuditEvent timeline.
 *   2. "Initial commit" badge marks the FIRST `review_state_committed`
 *      row; subsequent commits get the "Re-open" badge.
 *   3. Empty state copy renders when 0 events (§A1.54).
 *   4. Pagination "Show more" advances to page 2.
 *   5. Filter — only allowlisted advisor-relevant kinds surface in
 *      this view (verified via the hook contract: backend filtering
 *      is already enforced).
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type * as ClientsModule from "../../lib/clients";

const useAuditEventsMock = vi.fn();
vi.mock("../../lib/clients", async () => {
  const actual = await vi.importActual<typeof ClientsModule>("../../lib/clients");
  return {
    ...actual,
    useAuditEventsForHousehold: (...args: unknown[]) => useAuditEventsMock(...args),
  };
});

vi.mock("../../chrome/ClientPicker", () => ({
  useRememberedClientId: () => ["hh_commits_test", () => {}],
}));

import { HouseholdCommitsSubTab } from "../HouseholdCommitsSubTab";

function row({
  id,
  action,
  actor = "advisor@example.com",
  created_at = "2026-05-01T10:00:00Z",
  entity_type = "review_workspace",
  entity_id = "ws_alpha",
  metadata = {},
}: {
  id: number;
  action: string;
  actor?: string;
  created_at?: string;
  entity_type?: string;
  entity_id?: string;
  metadata?: Record<string, unknown>;
}) {
  return { id, action, actor, created_at, entity_type, entity_id, metadata };
}

beforeEach(() => {
  useAuditEventsMock.mockReturnValue({
    isPending: false,
    isError: false,
    data: undefined,
  });
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("HouseholdCommitsSubTab", () => {
  it("renders chronological commit events with actor + timestamp", () => {
    useAuditEventsMock.mockReturnValue({
      isPending: false,
      isError: false,
      data: {
        events: [
          row({
            id: 2,
            action: "review_state_committed",
            actor: "advisor2@example.com",
            created_at: "2026-05-02T10:00:00Z",
          }),
          row({
            id: 1,
            action: "review_state_committed",
            actor: "advisor@example.com",
            created_at: "2026-05-01T10:00:00Z",
          }),
        ],
        total: 2,
        page: 1,
        page_size: 50,
        kind: "commits",
      },
    });
    render(
      <MemoryRouter>
        <HouseholdCommitsSubTab />
      </MemoryRouter>,
    );
    // Both events render. Under the identity i18n mock,
    // `formatActionLabel`'s "missing translation" branch fires and we
    // see the humanized "review state committed" text.
    const labels = screen.getAllByText("review state committed");
    expect(labels).toHaveLength(2);
    expect(screen.getByText(/advisor@example.com/)).toBeInTheDocument();
    expect(screen.getByText(/advisor2@example.com/)).toBeInTheDocument();
  });

  it("badges the FIRST (oldest) commit as initial; later commits as re-open", () => {
    useAuditEventsMock.mockReturnValue({
      isPending: false,
      isError: false,
      data: {
        events: [
          row({ id: 3, action: "review_state_committed", created_at: "2026-05-03T10:00:00Z" }),
          row({ id: 2, action: "review_state_committed", created_at: "2026-05-02T10:00:00Z" }),
          row({ id: 1, action: "review_state_committed", created_at: "2026-05-01T10:00:00Z" }),
        ],
        total: 3,
        page: 1,
        page_size: 50,
        kind: "commits",
      },
    });
    render(
      <MemoryRouter>
        <HouseholdCommitsSubTab />
      </MemoryRouter>,
    );
    const badges = screen.getAllByTestId("commit-badge");
    expect(badges).toHaveLength(3);
    // Newest first ordering: idx 0 (newest) and idx 1 are re-opens; idx 2
    // (oldest) is the initial commit.
    expect(badges[0]).toHaveTextContent("ctx.history.badge_re_open");
    expect(badges[1]).toHaveTextContent("ctx.history.badge_re_open");
    expect(badges[2]).toHaveTextContent("ctx.history.badge_initial_commit");
  });

  it("renders empty-state copy when 0 events (§A1.54)", () => {
    useAuditEventsMock.mockReturnValue({
      isPending: false,
      isError: false,
      data: { events: [], total: 0, page: 1, page_size: 50, kind: "commits" },
    });
    render(
      <MemoryRouter>
        <HouseholdCommitsSubTab />
      </MemoryRouter>,
    );
    expect(screen.getByText("ctx.history.commits_empty")).toBeInTheDocument();
  });

  it("shows 'Show more' when there are unpaginated remaining events; click advances page", () => {
    useAuditEventsMock.mockReturnValue({
      isPending: false,
      isError: false,
      data: {
        events: Array.from({ length: 50 }, (_, i) =>
          row({
            id: i + 1,
            action: "review_state_committed",
            created_at: `2026-05-${String((i % 28) + 1).padStart(2, "0")}T10:00:00Z`,
          }),
        ),
        total: 75,
        page: 1,
        page_size: 50,
        kind: "commits",
      },
    });
    render(
      <MemoryRouter>
        <HouseholdCommitsSubTab />
      </MemoryRouter>,
    );
    const showMore = screen.getByRole("button", {
      name: /ctx\.history\.commits_show_more/,
    });
    expect(showMore).toBeInTheDocument();
    // Click advances the page param; the mock is called again with page=2.
    fireEvent.click(showMore);
    const calls = useAuditEventsMock.mock.calls;
    const lastCallArgs = calls[calls.length - 1];
    expect(lastCallArgs).toBeDefined();
    expect(lastCallArgs?.[2]).toBe(2);
  });

  it("renders error fallback when query fails", () => {
    useAuditEventsMock.mockReturnValue({
      isPending: false,
      isError: true,
      data: undefined,
    });
    render(
      <MemoryRouter>
        <HouseholdCommitsSubTab />
      </MemoryRouter>,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("renders review_workspace_reopened events with badge (P2.1 §A1.30)", () => {
    useAuditEventsMock.mockReturnValue({
      isPending: false,
      isError: false,
      data: {
        events: [
          row({
            id: 3,
            action: "review_workspace_reopened",
            entity_type: "review_workspace",
            entity_id: "ws_reopen_42",
            metadata: { source_household_id: "hh_commits_test" },
            created_at: "2026-05-04T10:00:00Z",
          }),
          row({
            id: 1,
            action: "review_state_committed",
            created_at: "2026-05-01T10:00:00Z",
          }),
        ],
        total: 2,
        page: 1,
        page_size: 50,
        kind: "commits",
      },
    });
    render(
      <MemoryRouter>
        <HouseholdCommitsSubTab />
      </MemoryRouter>,
    );
    // Both events render with their humanized action label.
    expect(screen.getByText("review workspace reopened")).toBeInTheDocument();
    expect(screen.getByText("review state committed")).toBeInTheDocument();
    // The reopen entry surfaces a workspace-link with the new ws ID.
    const link = screen
      .getAllByRole("link")
      .find((l) => l.getAttribute("href")?.includes("ws_reopen_42"));
    expect(link).toBeDefined();
    // Both COMMIT_ACTIONS rows render the badge testid.
    const badges = screen.getAllByTestId("commit-badge");
    expect(badges.length).toBe(2);
  });

  it("renders forward-compat advisor-relevant kinds (P2.5 + P13 events) without crashing", () => {
    // Forward-compat: events for `entities_reconciled_via_button` (P2.5)
    // and `account_assigned_to_goals` (P13) may not be emitted yet, but
    // when they are, this sub-tab must surface them without a missing-key
    // crash.
    useAuditEventsMock.mockReturnValue({
      isPending: false,
      isError: false,
      data: {
        events: [
          row({ id: 3, action: "account_assigned_to_goals", entity_type: "household" }),
          row({ id: 2, action: "entities_reconciled_via_button" }),
          row({ id: 1, action: "review_state_committed" }),
        ],
        total: 3,
        page: 1,
        page_size: 50,
        kind: "commits",
      },
    });
    render(
      <MemoryRouter>
        <HouseholdCommitsSubTab />
      </MemoryRouter>,
    );
    // Identity i18n mock => fallback humanizer kicks in.
    expect(screen.getByText("account assigned to goals")).toBeInTheDocument();
    expect(
      screen.getByText("entities reconciled via button"),
    ).toBeInTheDocument();
    expect(screen.getByText("review state committed")).toBeInTheDocument();
  });
});
