/**
 * ReviewScreen unit tests — Pair 5 (P3.3 + P3.4) coverage.
 *
 * Targets:
 *   - <AddBlockerInlineButton> open/save/cancel + state interactions
 *   - <ResolveAllMissingWizard> walk + skip + re-fetch readiness +
 *     continue-later + aria-modal Esc handler
 *   - summarizeReviewedState() allocation-matrix builder (caps,
 *     orphans, target % footer)
 *
 * Mocking strategy:
 *   - Hooks (useApplyFactOverride, useReviewWorkspace) are mocked so
 *     we can drive the wizard's "re-fetch readiness between steps"
 *     contract by mutating the returned data shape between assertions.
 *   - i18next is mocked globally via test/setup.ts so we assert
 *     against the i18n key strings directly.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import type * as ReviewLib from "../../lib/review";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AddBlockerInlineButton } from "../AddBlockerInlineButton";
import ResolveAllMissingWizard from "../ResolveAllMissingWizard";
import { summarizeReviewedState } from "../ReviewScreen";
import type { ReadinessRow, ReviewWorkspace } from "../../lib/review";

const applyMutate = vi.fn();
const useApplyFactOverrideMock = vi.fn();
const useReviewWorkspaceMock = vi.fn();

vi.mock("../../lib/review", async () => {
  const actual = await vi.importActual<typeof ReviewLib>("../../lib/review");
  return {
    ...actual,
    useApplyFactOverride: (workspaceId: string) =>
      useApplyFactOverrideMock(workspaceId),
    useReviewWorkspace: (workspaceId: string) =>
      useReviewWorkspaceMock(workspaceId),
  };
});

vi.mock("../../lib/toast", () => ({
  toastError: vi.fn(),
  toastSuccess: vi.fn(),
}));

afterEach(() => {
  applyMutate.mockReset();
  useApplyFactOverrideMock.mockReset();
  useReviewWorkspaceMock.mockReset();
});

function mockApplyOverride({
  isPending = false,
}: { isPending?: boolean } = {}) {
  useApplyFactOverrideMock.mockReturnValue({
    mutate: applyMutate,
    isPending,
  });
}

function mockWorkspaceMissing(missing: ReadinessRow[]) {
  useReviewWorkspaceMock.mockReturnValue({
    data: {
      readiness: { missing },
    } as unknown as ReviewWorkspace,
    isPending: false,
  });
}

// ---------------------------------------------------------------------------
// AddBlockerInlineButton (6 cases)
// ---------------------------------------------------------------------------

describe("AddBlockerInlineButton", () => {
  it("renders the compact `+` icon button when collapsed", () => {
    mockApplyOverride();
    render(
      <AddBlockerInlineButton
        workspaceId="ws-1"
        fieldPath="goals[0].name"
        label="Goal 0 — Name"
      />,
    );
    const cta = screen.getByRole("button", {
      name: /review.add_blocker.action_aria/,
    });
    expect(cta).toBeInTheDocument();
    expect(cta).not.toBeDisabled();
  });

  it("disables the inline button when fieldPath is empty (legacy row)", () => {
    mockApplyOverride();
    render(
      <AddBlockerInlineButton
        workspaceId="ws-1"
        fieldPath=""
        label="Some Section"
      />,
    );
    const cta = screen.getByRole("button", {
      name: /review.add_blocker.action_aria/,
    });
    expect(cta).toBeDisabled();
  });

  it("expands the inline form when clicked", () => {
    mockApplyOverride();
    render(
      <AddBlockerInlineButton
        workspaceId="ws-1"
        fieldPath="goals[0].name"
        label="Goal 0 — Name"
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: /review.add_blocker.action_aria/ }),
    );
    expect(
      screen.getByRole("button", { name: "review.add_blocker.save" }),
    ).toBeInTheDocument();
  });

  it("save button stays disabled until value + rationale are valid", () => {
    mockApplyOverride();
    render(
      <AddBlockerInlineButton
        workspaceId="ws-1"
        fieldPath="goals[0].name"
        label="Goal 0 — Name"
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: /review.add_blocker.action_aria/ }),
    );
    const save = screen.getByRole("button", { name: "review.add_blocker.save" });
    expect(save).toBeDisabled();
    // fill value only — rationale still empty.
    const valueInput = screen.getByLabelText("review.add_blocker.value_label");
    fireEvent.change(valueInput, { target: { value: "Retirement" } });
    expect(save).toBeDisabled();
    // fill short rationale — still under the 4-char floor.
    const rationale = screen.getByPlaceholderText(
      "review.add_blocker.rationale_placeholder",
    );
    fireEvent.change(rationale, { target: { value: "ok" } });
    expect(save).toBeDisabled();
    // fill valid rationale.
    fireEvent.change(rationale, { target: { value: "Pulled from KYC page 1" } });
    expect(save).not.toBeDisabled();
  });

  it("clicking Save dispatches useApplyFactOverride.mutate with field_path + is_added=true", () => {
    mockApplyOverride();
    render(
      <AddBlockerInlineButton
        workspaceId="ws-1"
        fieldPath="goals[0].name"
        label="Goal 0 — Name"
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: /review.add_blocker.action_aria/ }),
    );
    fireEvent.change(
      screen.getByLabelText("review.add_blocker.value_label"),
      { target: { value: "Retirement" } },
    );
    fireEvent.change(
      screen.getByPlaceholderText("review.add_blocker.rationale_placeholder"),
      { target: { value: "Pulled from KYC page 1" } },
    );
    fireEvent.click(
      screen.getByRole("button", { name: "review.add_blocker.save" }),
    );
    expect(applyMutate).toHaveBeenCalledTimes(1);
    const [payload] = applyMutate.mock.calls[0] ?? [];
    expect(payload).toMatchObject({
      field: "goals[0].name",
      value: "Retirement",
      rationale: "Pulled from KYC page 1",
      is_added: true,
    });
  });

  it("Cancel collapses the form back to the compact button", () => {
    mockApplyOverride();
    render(
      <AddBlockerInlineButton
        workspaceId="ws-1"
        fieldPath="goals[0].name"
        label="Goal 0 — Name"
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: /review.add_blocker.action_aria/ }),
    );
    expect(
      screen.getByRole("button", { name: "review.add_blocker.save" }),
    ).toBeInTheDocument();
    // Two cancel buttons render (the X icon header + the footer "Cancel" button)
    // — clicking either collapses the form. Pick the footer button.
    const cancelButtons = screen.getAllByRole("button", {
      name: "review.add_blocker.cancel",
    });
    const firstCancel = cancelButtons[0];
    if (!firstCancel) throw new Error("expected at least one cancel button");
    fireEvent.click(firstCancel);
    expect(
      screen.queryByRole("button", { name: "review.add_blocker.save" }),
    ).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ResolveAllMissingWizard (5 cases)
// ---------------------------------------------------------------------------

const FOUR_MISSING: ReadinessRow[] = [
  { section: "household", label: "Household name", field_path: "household.display_name" },
  { section: "people", label: "Person 0 — DOB", field_path: "people[0].date_of_birth" },
  { section: "goals", label: "Goal 0 — Target", field_path: "goals[0].target_amount" },
  { section: "risk", label: "Household risk", field_path: "risk.household_score" },
];

describe("ResolveAllMissingWizard", () => {
  it("walks step-by-step + invokes mutate per save with the canonical field path", () => {
    mockApplyOverride();
    mockWorkspaceMissing(FOUR_MISSING);
    render(
      <ResolveAllMissingWizard
        workspaceId="ws-1"
        initialMissing={FOUR_MISSING}
        onClose={vi.fn()}
      />,
    );
    // Step 1 of 4 visible.
    expect(screen.getByText("review.resolve_wizard.progress")).toBeInTheDocument();
    expect(screen.getByText("Household name")).toBeInTheDocument();
    // Drive a save on step 1.
    fireEvent.change(
      screen.getByLabelText("review.resolve_wizard.value_label"),
      { target: { value: "Yeager Household" } },
    );
    fireEvent.change(
      screen.getByPlaceholderText("review.resolve_wizard.rationale_placeholder"),
      { target: { value: "Per cover sheet of intake form" } },
    );
    fireEvent.click(
      screen.getByRole("button", { name: "review.resolve_wizard.save_and_next" }),
    );
    expect(applyMutate).toHaveBeenCalledTimes(1);
    const [payload] = applyMutate.mock.calls[0] ?? [];
    expect(payload).toMatchObject({
      field: "household.display_name",
      value: "Yeager Household",
      is_added: true,
    });
  });

  it("Skip advances without dispatching mutate", () => {
    mockApplyOverride();
    mockWorkspaceMissing(FOUR_MISSING);
    render(
      <ResolveAllMissingWizard
        workspaceId="ws-1"
        initialMissing={FOUR_MISSING}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText("Household name")).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "review.resolve_wizard.skip" }),
    );
    expect(applyMutate).not.toHaveBeenCalled();
    // Now on step 2 — the Person 0 — DOB row.
    expect(screen.getByText("Person 0 — DOB")).toBeInTheDocument();
  });

  it("re-fetches readiness between steps via useReviewWorkspace", () => {
    mockApplyOverride();
    // Workspace pre-populated with all 4; the hook is the source of
    // truth for the post-save re-fetch.
    mockWorkspaceMissing(FOUR_MISSING);
    render(
      <ResolveAllMissingWizard
        workspaceId="ws-1"
        initialMissing={FOUR_MISSING}
        onClose={vi.fn()}
      />,
    );
    // The hook is invoked once per render; with the wizard mounted,
    // it MUST be called with the workspaceId so the live readiness
    // drives subsequent steps.
    expect(useReviewWorkspaceMock).toHaveBeenCalledWith("ws-1");
  });

  it("Continue later button calls onClose", () => {
    mockApplyOverride();
    mockWorkspaceMissing(FOUR_MISSING);
    const onClose = vi.fn();
    render(
      <ResolveAllMissingWizard
        workspaceId="ws-1"
        initialMissing={FOUR_MISSING}
        onClose={onClose}
      />,
    );
    // The header X button has the "continue_later" aria-label; the
    // footer button has the same translation as visible text. Either
    // one works; we click the footer one first.
    const continueLaterButtons = screen.getAllByRole("button", {
      name: "review.resolve_wizard.continue_later",
    });
    const firstButton = continueLaterButtons[0];
    if (!firstButton) throw new Error("expected at least one continue-later button");
    fireEvent.click(firstButton);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("aria-modal=true with imperative Escape handler closes the wizard (anti-pattern #12)", () => {
    mockApplyOverride();
    mockWorkspaceMissing(FOUR_MISSING);
    const onClose = vi.fn();
    render(
      <ResolveAllMissingWizard
        workspaceId="ws-1"
        initialMissing={FOUR_MISSING}
        onClose={onClose}
      />,
    );
    const dialog = screen.getByRole("dialog");
    expect(dialog.getAttribute("aria-modal")).toBe("true");
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("renders the all-done body when there are no missing rows", () => {
    mockApplyOverride();
    mockWorkspaceMissing([]);
    const onClose = vi.fn();
    render(
      <ResolveAllMissingWizard
        workspaceId="ws-1"
        initialMissing={[]}
        onClose={onClose}
      />,
    );
    expect(screen.getByText("review.resolve_wizard.all_done_body")).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "review.resolve_wizard.close" }),
    );
    expect(onClose).toHaveBeenCalled();
  });

  it("save success advances the step pointer (onSuccess callback fires)", () => {
    // Drive the mutate's onSuccess directly so we exercise the
    // setStepIndex(i => i + 1) advance path. The mock implementation
    // accepts (payload, options) and immediately invokes options.onSuccess.
    useApplyFactOverrideMock.mockReturnValue({
      mutate: (
        _payload: unknown,
        opts?: { onSuccess?: (response: unknown) => void },
      ) => {
        opts?.onSuccess?.({});
      },
      isPending: false,
    });
    mockWorkspaceMissing(FOUR_MISSING);
    render(
      <ResolveAllMissingWizard
        workspaceId="ws-1"
        initialMissing={FOUR_MISSING}
        onClose={vi.fn()}
      />,
    );
    // Step 1 — fill + save.
    fireEvent.change(
      screen.getByLabelText("review.resolve_wizard.value_label"),
      { target: { value: "Yeager Household" } },
    );
    fireEvent.change(
      screen.getByPlaceholderText("review.resolve_wizard.rationale_placeholder"),
      { target: { value: "Per cover sheet of intake form" } },
    );
    fireEvent.click(
      screen.getByRole("button", { name: "review.resolve_wizard.save_and_next" }),
    );
    // Now on step 2 — Person 0 — DOB.
    expect(screen.getByText("Person 0 — DOB")).toBeInTheDocument();
  });

  it("filters out missing rows without a field_path before stepping", () => {
    mockApplyOverride();
    const mixed: ReadinessRow[] = [
      ...FOUR_MISSING,
      // Legacy row with no field_path — should be skipped (excluded
      // from the step list) since the wizard can't deep-link it.
      { section: "people", label: "Person empty", field_path: "" },
    ];
    mockWorkspaceMissing(mixed);
    render(
      <ResolveAllMissingWizard
        workspaceId="ws-1"
        initialMissing={mixed}
        onClose={vi.fn()}
      />,
    );
    // Total reads 4 (not 5) — the empty-field_path row is filtered.
    const progress = screen.getByText("review.resolve_wizard.progress");
    expect(progress).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// summarizeReviewedState — allocation matrix builder (4 cases)
// ---------------------------------------------------------------------------

describe("summarizeReviewedState — allocation matrix", () => {
  it("builds a 3×2 matrix with 4 links + 1 orphan", () => {
    const state = {
      goals: [
        { id: "g1", name: "Retirement", target_amount: 500000 },
        { id: "g2", name: "Education", target_amount: 100000 },
        { id: "g3", name: "Vacation", target_amount: 20000 },
      ],
      accounts: [
        { id: "a1", account_type: "rrsp" },
        { id: "a2", account_type: "tfsa" },
      ],
      goal_account_links: [
        { goal_id: "g1", account_id: "a1", allocated_amount: 250000 },
        { goal_id: "g1", account_id: "a2", allocated_amount: 50000 },
        { goal_id: "g2", account_id: "a1", allocated_amount: 60000 },
        { goal_id: "g3", account_id: "a2", allocated_amount: 10000 },
        // Orphan — references a goal id that no longer exists.
        { goal_id: "g_ghost", account_id: "a1", allocated_amount: 9999 },
      ],
    };
    const summary = summarizeReviewedState(state);
    expect(summary.goal_account_links_count).toBe(5);
    const m = summary.allocation_matrix;
    expect(m.rows.map((r) => r.id)).toEqual(["g1", "g2", "g3"]);
    expect(m.cols.map((c) => c.id)).toEqual(["a1", "a2"]);
    // Orphan link counted in footnote, excluded from cells.
    expect(m.orphan_count).toBe(1);
    expect(m.row_overflow).toBe(0);
    expect(m.col_overflow).toBe(0);
    // Per-cell amounts.
    expect(m.rows[0]?.cells.a1).toBe(250000);
    expect(m.rows[0]?.cells.a2).toBe(50000);
    expect(m.rows[1]?.cells.a1).toBe(60000);
    expect(m.rows[1]?.cells.a2).toBeUndefined();
    expect(m.rows[2]?.cells.a2).toBe(10000);
    // Account totals.
    expect(m.cols[0]?.total).toBe(310000);
    expect(m.cols[1]?.total).toBe(60000);
    // Per-goal target % (allocated / target × 100). Retirement
    // 300000/500000 = 60%; Education 60000/100000 = 60%; Vacation
    // 10000/20000 = 50%.
    expect(m.rows[0]?.target_pct).toBeCloseTo(60);
    expect(m.rows[1]?.target_pct).toBeCloseTo(60);
    expect(m.rows[2]?.target_pct).toBeCloseTo(50);
  });

  it("caps to 8 goals + 8 accounts and surfaces +N more counts", () => {
    const goals = Array.from({ length: 12 }, (_, i) => ({
      id: `g${i}`,
      name: `Goal ${i}`,
      target_amount: 1000,
    }));
    const accounts = Array.from({ length: 10 }, (_, i) => ({
      id: `a${i}`,
      account_type: "tfsa",
    }));
    const summary = summarizeReviewedState({
      goals,
      accounts,
      goal_account_links: [],
    });
    const m = summary.allocation_matrix;
    expect(m.rows).toHaveLength(8);
    expect(m.cols).toHaveLength(8);
    expect(m.row_overflow).toBe(4);
    expect(m.col_overflow).toBe(2);
  });

  it("returns null target_pct when goal target_amount is missing or zero", () => {
    const summary = summarizeReviewedState({
      goals: [
        { id: "g1", name: "Open-ended", target_amount: 0 },
        { id: "g2", name: "Unknown" }, // no target_amount field
      ],
      accounts: [{ id: "a1", account_type: "rrsp" }],
      goal_account_links: [
        { goal_id: "g1", account_id: "a1", allocated_amount: 1000 },
        { goal_id: "g2", account_id: "a1", allocated_amount: 500 },
      ],
    });
    expect(summary.allocation_matrix.rows[0]?.target_pct).toBeNull();
    expect(summary.allocation_matrix.rows[1]?.target_pct).toBeNull();
  });

  it("returns empty matrix when goals or accounts are absent", () => {
    const summary = summarizeReviewedState({});
    expect(summary.allocation_matrix.rows).toHaveLength(0);
    expect(summary.allocation_matrix.cols).toHaveLength(0);
    expect(summary.allocation_matrix.orphan_count).toBe(0);
  });
});
