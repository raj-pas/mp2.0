/**
 * UnallocatedBanner — plan v20 §A1.36 (P12 / G12).
 *
 * Coverage:
 *   1. Renders when `account.current_value > sum(legs.allocated_amount)`.
 *   2. Hidden (returns null) when fully allocated (§A1.54 empty state).
 *   3. CTA `onAssignClick` fires with the correct `account_id` (§A1.51
 *      cross-phase contract — P13 wires AssignAccountModal to this
 *      callback signature).
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../../lib/toast", () => ({
  toastError: vi.fn(),
  toastSuccess: vi.fn(),
}));

import {
  UnallocatedBanner,
  unallocatedAccountsForHousehold,
} from "../UnallocatedBanner";
import { mockAccount, mockGoal, mockGoalAccountLink } from "../../__tests__/__fixtures__/household";

describe("unallocatedAccountsForHousehold", () => {
  it("returns rows where allocated < current_value", () => {
    const household = {
      goals: [
        mockGoal({
          id: "goal_x",
          account_allocations: [
            mockGoalAccountLink({
              id: "link_x",
              goal_id: "goal_x",
              account_id: "acct_partial",
              allocated_amount: 10000,
            }),
          ],
        }),
      ],
      accounts: [
        mockAccount({ id: "acct_partial", current_value: 100000, is_held_at_purpose: true }),
      ],
    };
    const rows = unallocatedAccountsForHousehold(household);
    expect(rows).toHaveLength(1);
    expect(rows[0]).toEqual(
      expect.objectContaining({
        account_id: "acct_partial",
        allocated_amount: 10000,
        current_value: 100000,
        unallocated_amount: 90000,
      }),
    );
  });

  it("returns empty array when fully allocated (penny tolerance respected)", () => {
    const household = {
      goals: [
        mockGoal({
          account_allocations: [
            mockGoalAccountLink({
              account_id: "acct_full",
              allocated_amount: 100000,
            }),
          ],
        }),
      ],
      accounts: [
        mockAccount({ id: "acct_full", current_value: 100000, is_held_at_purpose: true }),
      ],
    };
    expect(unallocatedAccountsForHousehold(household)).toEqual([]);
  });

  it("excludes external (non-Purpose) accounts from unallocated rows", () => {
    const household = {
      goals: [],
      accounts: [
        mockAccount({ id: "acct_external", current_value: 50000, is_held_at_purpose: false }),
      ],
    };
    expect(unallocatedAccountsForHousehold(household)).toEqual([]);
  });
});

describe("UnallocatedBanner", () => {
  it("renders headline + per-account row when unallocated > 0", () => {
    const household = {
      goals: [
        mockGoal({
          account_allocations: [
            mockGoalAccountLink({ account_id: "acct_a", allocated_amount: 25000 }),
          ],
        }),
      ],
      accounts: [
        mockAccount({
          id: "acct_a",
          type: "RRSP",
          current_value: 100000,
          is_held_at_purpose: true,
        }),
      ],
    };
    render(<UnallocatedBanner household={household} />);
    expect(screen.getByTestId("unallocated-banner")).toBeInTheDocument();
    // Per-account assign button
    expect(
      screen.getByRole("button", { name: /unallocated_banner\.cta_per_account_aria/ }),
    ).toBeInTheDocument();
  });

  it("returns null when household is fully allocated (§A1.54 empty state)", () => {
    const household = {
      goals: [
        mockGoal({
          account_allocations: [
            mockGoalAccountLink({ account_id: "acct_full", allocated_amount: 100000 }),
          ],
        }),
      ],
      accounts: [
        mockAccount({ id: "acct_full", current_value: 100000, is_held_at_purpose: true }),
      ],
    };
    const { container } = render(<UnallocatedBanner household={household} />);
    expect(container.firstChild).toBeNull();
    expect(screen.queryByTestId("unallocated-banner")).toBeNull();
  });

  it("CTA fires onAssignClick with the correct account_id (§A1.51 P13 contract)", () => {
    const onAssignClick = vi.fn();
    const household = {
      goals: [
        mockGoal({
          account_allocations: [
            mockGoalAccountLink({ account_id: "acct_x", allocated_amount: 0 }),
          ],
        }),
      ],
      accounts: [
        mockAccount({
          id: "acct_x",
          type: "TFSA",
          current_value: 50000,
          is_held_at_purpose: true,
        }),
      ],
    };
    render(<UnallocatedBanner household={household} onAssignClick={onAssignClick} />);
    fireEvent.click(
      screen.getByRole("button", { name: /unallocated_banner\.cta_per_account_aria/ }),
    );
    expect(onAssignClick).toHaveBeenCalledWith({ account_id: "acct_x" });
  });
});
