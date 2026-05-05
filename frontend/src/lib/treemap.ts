import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "./api";
import { canonizeFundId, FUND_COLOR_BY_CANON } from "./funds";

export type TreemapMode = "by_account" | "by_goal" | "by_fund" | "by_asset";

export type TreemapNode = {
  id: string;
  label: string;
  value?: number;
  children?: TreemapNode[];
  /**
   * Plan v20 §A1.36 (P12 / G12): set on virtual `_unallocated` /
   * `_unassigned` nodes that the backend emits when an account has
   * `current_value > sum(legs.allocated_amount)`. Frontend renders
   * with dashed border + striped pattern + click → AssignAccountModal.
   */
  unallocated?: boolean;
  /** Account ID of the unallocated parent — used by the click handler
   *  to pre-focus the AssignAccountModal (P13 wires the modal). */
  account_id?: string;
};

export type TreemapPayload = {
  mode: TreemapMode;
  household_id: string;
  data: TreemapNode;
};

export const treemapQueryKey = (id: string, mode: TreemapMode) => ["treemap", id, mode] as const;

export function useTreemap(householdId: string | null, mode: TreemapMode) {
  return useQuery<TreemapPayload>({
    queryKey: householdId ? treemapQueryKey(householdId, mode) : ["treemap", "_none", mode],
    queryFn: () => {
      if (householdId === null) {
        return Promise.reject(new Error("household id is required"));
      }
      const params = new URLSearchParams({ household_id: householdId, mode });
      return apiFetch<TreemapPayload>(`/api/treemap/?${params.toString()}`);
    },
    enabled: householdId !== null,
  });
}

const ASSET_COLOR: Record<string, string> = {
  "ASSET_CLASS:CANADIAN_EQUITY": "#5D7A8C",
  "ASSET_CLASS:US_EQUITY": "#2E4A6B",
  "ASSET_CLASS:INTERNATIONAL_EQUITY": "#8B5E3C",
  "ASSET_CLASS:EMERGING_EQUITY": "#B87333",
  "ASSET_CLASS:CORE_FIXED_INCOME": "#6B8E8E",
  "ASSET_CLASS:CASH": "#9CA3AF",
  "ASSET_CLASS:REAL_ASSETS": "#6B5876",
};

const FALLBACK_PALETTE = [
  "#5D7A8C",
  "#2E4A6B",
  "#8B5E3C",
  "#B87333",
  "#2E5D3A",
  "#6B5876",
  "#8B8C5E",
  "#6B8E8E",
];

const DEFAULT_FILL = "#9CA3AF";

function fallbackColor(index: number): string {
  return FALLBACK_PALETTE[index % FALLBACK_PALETTE.length] ?? DEFAULT_FILL;
}

export function colorForNode(node: TreemapNode, mode: TreemapMode, index: number): string {
  if (mode === "by_fund") {
    const canon = canonizeFundId(node.id);
    if (canon !== null) return FUND_COLOR_BY_CANON[canon];
    return fallbackColor(index);
  }
  if (mode === "by_asset") {
    return ASSET_COLOR[node.id] ?? fallbackColor(index);
  }
  return fallbackColor(index);
}
