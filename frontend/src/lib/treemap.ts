import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "./api";

export type TreemapMode = "by_account" | "by_goal" | "by_fund" | "by_asset";

export type TreemapNode = {
  id: string;
  label: string;
  value?: number;
  children?: TreemapNode[];
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

const FUND_COLOR_BY_ID: Record<string, string> = {
  "sh-sav": "#5D7A8C",
  "sh-inc": "#2E4A6B",
  "sh-eq": "#0E1116",
  "sh-glb": "#8B5E3C",
  "sh-sc": "#B87333",
  "sh-gsc": "#2E5D3A",
  "sh-fnd": "#6B5876",
  "sh-bld": "#8B8C5E",
};

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
    return FUND_COLOR_BY_ID[node.id] ?? fallbackColor(index);
  }
  if (mode === "by_asset") {
    return ASSET_COLOR[node.id] ?? fallbackColor(index);
  }
  return fallbackColor(index);
}
