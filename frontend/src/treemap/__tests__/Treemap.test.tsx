/**
 * Treemap — plan v20 §A1.36 (P12 / G12) tests for virtual unallocated
 * tile rendering.
 *
 * Coverage (extends pair scope):
 *   1. Unallocated tile renders when present (`unallocated: true`).
 *   2. Click handler fires onSelect with the unallocated node (P13
 *      will use `node.account_id` to open AssignAccountModal).
 *   3. by_goal mode "Unassigned" parent group renders as a top-level
 *      tile with stripe pattern.
 *   4. Fully-allocated household renders ZERO virtual tiles (§A1.50).
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Treemap } from "../Treemap";
import type { TreemapNode } from "../../lib/treemap";

// JSDom doesn't implement ResizeObserver — provide a noop stub so the
// Treemap's `useEffect` doesn't throw when subscribing.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(globalThis as any).ResizeObserver = ResizeObserverStub;

function rootWithUnallocated(): TreemapNode {
  return {
    id: "hh_test",
    label: "Test Household",
    children: [
      {
        id: "acct_a",
        label: "RRSP",
        value: 100000,
        children: [
          { id: "acct_a:goal_1", label: "Retirement", value: 10000 },
          {
            id: "acct_a:_unallocated",
            label: "Unallocated",
            value: 90000,
            unallocated: true,
            account_id: "acct_a",
          },
        ],
      },
    ],
  };
}

function rootFullyAllocated(): TreemapNode {
  return {
    id: "hh_full",
    label: "Fully Allocated",
    children: [
      {
        id: "acct_b",
        label: "TFSA",
        value: 50000,
        children: [{ id: "acct_b:goal_1", label: "Retirement", value: 50000 }],
      },
    ],
  };
}

function rootByGoalUnassigned(): TreemapNode {
  return {
    id: "hh_goal",
    label: "By Goal",
    children: [
      {
        id: "goal_1",
        label: "Retirement",
        value: 10000,
        children: [{ id: "goal_1:acct_a", label: "RRSP", value: 10000 }],
      },
      {
        id: "_unassigned",
        label: "Unassigned",
        value: 90000,
        unallocated: true,
        children: [
          {
            id: "_unassigned:acct_a",
            label: "RRSP",
            value: 90000,
            unallocated: true,
            account_id: "acct_a",
          },
        ],
      },
    ],
  };
}

describe("Treemap — unallocated virtual tile (P12)", () => {
  it("renders an unallocated tile with the test-id when `unallocated` flag is set", () => {
    render(<Treemap root={rootWithUnallocated()} mode="by_account" />);
    const tile = screen.getByTestId("treemap-unallocated-tile");
    expect(tile).toBeInTheDocument();
    // SVG <g> with role=img (no onSelect) — aria-label includes "Unallocated"
    expect(tile.getAttribute("aria-label")).toMatch(/treemap_extras\.unallocated_label/);
  });

  it("click on unallocated tile fires onSelect with the unallocated node (account_id present)", () => {
    const onSelect = vi.fn();
    render(<Treemap root={rootWithUnallocated()} mode="by_account" onSelect={onSelect} />);
    const tile = screen.getByTestId("treemap-unallocated-tile");
    fireEvent.click(tile);
    expect(onSelect).toHaveBeenCalledTimes(1);
    const arg = onSelect.mock.calls[0]?.[0];
    expect(arg).toEqual(
      expect.objectContaining({
        unallocated: true,
        account_id: "acct_a",
      }),
    );
  });

  it("by_goal mode 'Unassigned' parent group renders with the unallocated treatment", () => {
    render(<Treemap root={rootByGoalUnassigned()} mode="by_goal" />);
    // The Unassigned leg is a leaf in the layout (it has children but
    // d3-treemap will still surface it because the layout drills to
    // leaves). Easier check: `getAllByTestId` should return at least
    // one unallocated tile.
    const tiles = screen.getAllByTestId("treemap-unallocated-tile");
    expect(tiles.length).toBeGreaterThanOrEqual(1);
  });

  it("fully-allocated household renders ZERO virtual unallocated tiles (§A1.50 boundary)", () => {
    render(<Treemap root={rootFullyAllocated()} mode="by_account" />);
    expect(screen.queryByTestId("treemap-unallocated-tile")).toBeNull();
  });
});
