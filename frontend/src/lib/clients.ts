import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "./api";

/**
 * Lightweight household summary served by the existing
 * `ClientListView` (advisor-only). Matches the shape of
 * `HouseholdListSerializer` on the backend.
 */
export type ClientSummary = {
  external_id: string;
  name: string;
  total_aum?: number | null;
  goal_count?: number;
  account_count?: number;
};

export const CLIENTS_QUERY_KEY = ["clients"] as const;

export function useClients(enabled = true) {
  return useQuery<ClientSummary[]>({
    queryKey: CLIENTS_QUERY_KEY,
    queryFn: () => apiFetch<ClientSummary[]>("/api/clients/"),
    enabled,
  });
}
