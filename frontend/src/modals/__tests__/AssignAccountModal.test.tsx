/**
 * AssignAccountModal — plan v20 §A1.28 (P13).
 *
 * Coverage (~10 cases per §A1.50):
 *   1. Renders header + intro with account + amount when open
 *   2. Pre-seeds rows from existing GoalAccountLinks
 *   3. Sum-validator labels match assigned/total/pct
 *   4. Submit button disabled when sum < 100%
 *   5. Submit button disabled when rationale < 4 chars
 *   6. Submit button enabled when 100% allocated + rationale ≥ 4 chars
 *   7. $-input updates corresponding %-input via live conversion (§A1.14 #12)
 *   8. %-input updates corresponding $-input via live conversion
 *   9. New-goal row exposes full inline-create fields (§A1.14 #17)
 *  10. Submit fires mutation with correct payload (rationale + assignments)
 *  11. onError → toastError fires (§A1.55 network failure)
 *  12. Closed state (open=false) renders nothing
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type * as householdModule from "../../lib/household";

// vi.mock factories are hoisted to the top of the file BEFORE any
// `const` declarations resolve, so we cannot reference outer-scope
// `vi.fn()` instances. Instead, attach mocks to a dedicated module-
// scope object that the factory closures over after hoist resolves.
const mocks = vi.hoisted(() => ({
  mutate: vi.fn(),
  toastError: vi.fn(),
  toastSuccess: vi.fn(),
}));

vi.mock("../../lib/household", async () => {
  const actual = await vi.importActual<typeof householdModule>(
    "../../lib/household",
  );
  return {
    ...actual,
    useAssignAccountToGoals: () => ({
      mutate: mocks.mutate,
      isPending: false,
    }),
  };
});

vi.mock("../../lib/toast", () => ({
  toastError: mocks.toastError,
  toastSuccess: mocks.toastSuccess,
}));

import AssignAccountModal from "../AssignAccountModal";
import {
  mockHousehold,
  mockAccount,
  mockGoal,
  mockGoalAccountLink,
} from "../../__tests__/__fixtures__/household";

afterEach(() => {
  mocks.mutate.mockReset();
  mocks.toastError.mockReset();
  mocks.toastSuccess.mockReset();
});

type AssignAccountModalProps = Parameters<typeof AssignAccountModal>[0];

function renderModal(props?: Partial<AssignAccountModalProps>) {
  const account = mockAccount({
    id: "acct_modal",
    type: "RRSP",
    current_value: 100000,
    is_held_at_purpose: true,
  });
  const goalA = mockGoal({
    id: "goal_a",
    name: "Goal A",
    account_allocations: [
      mockGoalAccountLink({
        id: "link_a",
        goal_id: "goal_a",
        account_id: "acct_modal",
        allocated_amount: 60000,
      }),
    ],
  });
  const goalB = mockGoal({
    id: "goal_b",
    name: "Goal B",
    account_allocations: [
      mockGoalAccountLink({
        id: "link_b",
        goal_id: "goal_b",
        account_id: "acct_modal",
        allocated_amount: 40000,
      }),
    ],
  });
  const household = mockHousehold({
    accounts: [account],
    goals: [goalA, goalB],
  });
  const onOpenChange = vi.fn();
  const onAssigned = vi.fn();
  render(
    <AssignAccountModal
      open
      onOpenChange={onOpenChange}
      household={household}
      accountId="acct_modal"
      onAssigned={onAssigned}
      {...props}
    />,
  );
  return { household, onOpenChange, onAssigned };
}

describe("AssignAccountModal", () => {
  it("renders header + intro with account + amount when open", () => {
    renderModal();
    expect(screen.getByText(/assign_account\.title/)).toBeInTheDocument();
  });

  it("pre-seeds rows from existing GoalAccountLinks", () => {
    renderModal();
    const rows = screen.getAllByTestId("assign-row");
    expect(rows).toHaveLength(2);
    const inputs = rows
      .flatMap((row) => Array.from(row.querySelectorAll<HTMLInputElement>("input")))
      .filter((i) => i.getAttribute("aria-label")?.includes("dollars_label"));
    // Pre-seeded values from existing links: $60k + $40k = $100k.
    const seededValues = inputs.map((i) => i.value);
    expect(seededValues).toContain("60000.00");
    expect(seededValues).toContain("40000.00");
  });

  it("sum-validator renders + reflects success-state class when balanced", () => {
    renderModal();
    const sumLabel = screen.getByTestId("assign-sum-validator");
    expect(sumLabel).toBeInTheDocument();
    // i18n keys are identity-mapped in tests (per src/test/setup.ts), so
    // we assert the success-color class is applied (state-driven CSS).
    expect(sumLabel.className).toMatch(/text-success/);
  });

  it("sum-validator switches to warning class when sum < 100%", () => {
    renderModal();
    const rows = screen.getAllByTestId("assign-row");
    const dollarInputs = rows.flatMap((r) =>
      Array.from(r.querySelectorAll<HTMLInputElement>("input")).filter(
        (i) => i.getAttribute("aria-label")?.includes("dollars_label"),
      ),
    );
    const firstDollarInput = dollarInputs[0];
    if (firstDollarInput === undefined) throw new Error("missing dollar input row");
    fireEvent.change(firstDollarInput, { target: { value: "0" } });
    const sumLabel = screen.getByTestId("assign-sum-validator");
    expect(sumLabel.className).toMatch(/text-warning/);
  });

  it("submit button is disabled when rationale < 4 chars", () => {
    renderModal();
    const submit = screen.getByTestId("assign-submit") as HTMLButtonElement;
    expect(submit.disabled).toBe(true);
    // Type only 3 chars
    const rationale = screen.getByLabelText(/rationale_label/) as HTMLTextAreaElement;
    fireEvent.change(rationale, { target: { value: "abc" } });
    expect(submit.disabled).toBe(true);
  });

  it("submit button is disabled when sum is not 100%", () => {
    renderModal();
    // Reduce one row to 50K so total is 90K (90%).
    const rows = screen.getAllByTestId("assign-row");
    const dollarInputs = rows.flatMap((r) =>
      Array.from(r.querySelectorAll<HTMLInputElement>("input")).filter(
        (i) => i.getAttribute("aria-label")?.includes("dollars_label"),
      ),
    );
    const firstDollarInput = dollarInputs[0];
    if (firstDollarInput === undefined) throw new Error("missing dollar input row");
    fireEvent.change(firstDollarInput, { target: { value: "50000" } });
    const rationale = screen.getByLabelText(/rationale_label/) as HTMLTextAreaElement;
    fireEvent.change(rationale, { target: { value: "valid rationale text" } });
    const submit = screen.getByTestId("assign-submit") as HTMLButtonElement;
    expect(submit.disabled).toBe(true);
  });

  it("submit button is enabled at 100% + rationale ≥ 4 chars", () => {
    renderModal();
    const rationale = screen.getByLabelText(/rationale_label/) as HTMLTextAreaElement;
    fireEvent.change(rationale, { target: { value: "valid rationale text" } });
    const submit = screen.getByTestId("assign-submit") as HTMLButtonElement;
    expect(submit.disabled).toBe(false);
  });

  it("$-input updates %-input via live conversion (§A1.14 #12)", () => {
    renderModal();
    const rows = screen.getAllByTestId("assign-row");
    const firstRow = rows[0];
    if (firstRow === undefined) throw new Error("missing first row");
    const dollarInput = firstRow.querySelector<HTMLInputElement>(
      'input[aria-label*="dollars_label"]',
    );
    const pctInput = firstRow.querySelector<HTMLInputElement>(
      'input[aria-label*="pct_label"]',
    );
    if (dollarInput === null || pctInput === null) throw new Error("missing inputs");
    fireEvent.change(dollarInput, { target: { value: "25000" } });
    // 25000 / 100000 = 25% — derived %-input updates.
    expect(pctInput.value).toBe("25.00");
  });

  it("%-input updates $-input via live conversion (§A1.14 #12)", () => {
    renderModal();
    const rows = screen.getAllByTestId("assign-row");
    const firstRow = rows[0];
    if (firstRow === undefined) throw new Error("missing first row");
    const dollarInput = firstRow.querySelector<HTMLInputElement>(
      'input[aria-label*="dollars_label"]',
    );
    const pctInput = firstRow.querySelector<HTMLInputElement>(
      'input[aria-label*="pct_label"]',
    );
    if (dollarInput === null || pctInput === null) throw new Error("missing inputs");
    fireEvent.change(pctInput, { target: { value: "10" } });
    // 10% of 100000 = 10000.
    expect(dollarInput.value).toBe("10000.00");
  });

  it("new-goal row exposes full inline-create fields (§A1.14 #17)", () => {
    renderModal();
    fireEvent.click(screen.getByTestId("add-new-goal"));
    expect(screen.getByLabelText(/new_goal\.name_label/)).toBeInTheDocument();
    expect(screen.getByLabelText(/new_goal\.target_label/)).toBeInTheDocument();
    expect(screen.getByLabelText(/new_goal\.target_date_label/)).toBeInTheDocument();
    expect(screen.getByLabelText(/new_goal\.necessity_label/)).toBeInTheDocument();
    expect(screen.getByLabelText(/new_goal\.risk_label/)).toBeInTheDocument();
  });

  it("submit fires mutation with correct payload", () => {
    renderModal();
    const rationale = screen.getByLabelText(/rationale_label/) as HTMLTextAreaElement;
    fireEvent.change(rationale, { target: { value: "valid rationale text" } });
    fireEvent.click(screen.getByTestId("assign-submit"));
    expect(mocks.mutate).toHaveBeenCalledTimes(1);
    const firstCall = mocks.mutate.mock.calls[0];
    if (firstCall === undefined) throw new Error("mutate not called");
    const [payload] = firstCall;
    expect(payload.rationale).toBe("valid rationale text");
    expect(payload.assignments).toHaveLength(2);
    // Existing-goal rows carry goal_id (string, not "new") + bp.
    payload.assignments.forEach((a: { goal_id: string; allocated_amount_basis_points: number }) => {
      expect(a.goal_id).not.toBe("new");
      expect(a.allocated_amount_basis_points).toBeGreaterThan(0);
    });
    const totalBp = payload.assignments.reduce(
      (s: number, a: { allocated_amount_basis_points: number }) => s + a.allocated_amount_basis_points,
      0,
    );
    expect(totalBp).toBe(1_000_000_000); // $100K * 10000 bp/dollar
  });

  it("onError surfaces toastError (§A1.55 network failure)", async () => {
    renderModal();
    const rationale = screen.getByLabelText(/rationale_label/) as HTMLTextAreaElement;
    fireEvent.change(rationale, { target: { value: "valid rationale text" } });
    // Stub mutate to invoke onError handler immediately.
    mocks.mutate.mockImplementation(
      (_payload: unknown, opts?: { onError?: (e: Error) => void }) => {
        opts?.onError?.(new Error("Internal server error 500"));
      },
    );
    fireEvent.click(screen.getByTestId("assign-submit"));
    await waitFor(() => expect(mocks.toastError).toHaveBeenCalled());
  });

  it("renders nothing when open=false", () => {
    const account = mockAccount({ id: "acct_modal", current_value: 100000 });
    const household = mockHousehold({ accounts: [account], goals: [] });
    const { container } = render(
      <AssignAccountModal
        open={false}
        onOpenChange={() => {}}
        household={household}
        accountId="acct_modal"
      />,
    );
    expect(container.querySelector("[data-testid='assign-rows']")).toBeNull();
  });

  it("renders nothing when accountId is null", () => {
    const account = mockAccount({ id: "acct_modal", current_value: 100000 });
    const household = mockHousehold({ accounts: [account], goals: [] });
    const { container } = render(
      <AssignAccountModal
        open
        onOpenChange={() => {}}
        household={household}
        accountId={null}
      />,
    );
    expect(container.querySelector("[data-testid='assign-rows']")).toBeNull();
  });
});
