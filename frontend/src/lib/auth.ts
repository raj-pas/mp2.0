import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "./api";

export type SessionUser = {
  email: string;
  name: string;
  role: "advisor" | "financial_analyst" | string;
  team: string | null;
  engine_enabled: boolean;
  disclaimer_acknowledged_at: string | null;
  disclaimer_acknowledged_version: string;
  tour_completed_at: string | null;
};

/**
 * Pilot disclaimer version. Bump when copy materially changes —
 * advisors see the banner again until they re-acknowledge, and the
 * audit log preserves every version each advisor saw.
 */
export const DISCLAIMER_VERSION = "v1";

export function useAcknowledgeDisclaimer() {
  const queryClient = useQueryClient();
  return useMutation<
    { acknowledged_at: string; version: string },
    Error,
    { version: string }
  >({
    mutationFn: ({ version }) =>
      apiFetch<{ acknowledged_at: string; version: string }>(
        "/api/disclaimer/acknowledge/",
        { method: "POST", body: { version } },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SESSION_QUERY_KEY });
    },
  });
}

export function useCompleteTour() {
  const queryClient = useQueryClient();
  return useMutation<{ completed_at: string }, Error, undefined>({
    mutationFn: () =>
      apiFetch<{ completed_at: string }>("/api/tour/complete/", {
        method: "POST",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SESSION_QUERY_KEY });
    },
  });
}

export function useSubmitFeedback() {
  return useMutation<
    { id: number; status: string },
    Error,
    {
      severity: "blocking" | "friction" | "suggestion";
      description: string;
      what_were_you_trying?: string;
      route?: string;
      session_id?: string;
    }
  >({
    mutationFn: (payload) =>
      apiFetch<{ id: number; status: string }>("/api/feedback/", {
        method: "POST",
        body: payload,
      }),
  });
}

export type SessionPayload =
  | { authenticated: true; csrf_token: string; user: SessionUser }
  | { authenticated: false; csrf_token: string; user: null };

export const SESSION_QUERY_KEY = ["session"] as const;

export function useSession() {
  return useQuery<SessionPayload>({
    queryKey: SESSION_QUERY_KEY,
    queryFn: () => apiFetch<SessionPayload>("/api/session/"),
    staleTime: 60 * 1000,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation<SessionPayload, Error, { email: string; password: string }>({
    mutationFn: ({ email, password }) =>
      apiFetch<SessionPayload>("/api/auth/login/", {
        method: "POST",
        body: { email, password },
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(SESSION_QUERY_KEY, data);
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation<{ ok: true }>({
    mutationFn: () => apiFetch<{ ok: true }>("/api/auth/logout/", { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SESSION_QUERY_KEY });
    },
  });
}

export function isAdvisorRole(role: string | undefined): boolean {
  return role === "advisor";
}

export function isAnalystRole(role: string | undefined): boolean {
  return role === "financial_analyst";
}
