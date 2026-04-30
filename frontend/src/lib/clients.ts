import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "./api";

/**
 * Lightweight household summary served by the existing
 * `ClientListView` (advisor-only). Matches the shape of
 * `HouseholdListSerializer` on the backend.
 */
export type ClientSummary = {
  id: string;
  display_name: string;
  household_type: string;
  household_risk_score: number | null;
  goal_count: number;
  total_assets: number;
};

export const CLIENTS_QUERY_KEY = ["clients"] as const;

export function useClients(enabled = true) {
  return useQuery<ClientSummary[]>({
    queryKey: CLIENTS_QUERY_KEY,
    queryFn: () => apiFetch<ClientSummary[]>("/api/clients/"),
    enabled,
  });
}
