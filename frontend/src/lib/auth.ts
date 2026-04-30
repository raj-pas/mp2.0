import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "./api";

export type SessionUser = {
  email: string;
  name: string;
  role: "advisor" | "financial_analyst" | string;
  team: string | null;
  engine_enabled: boolean;
};

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
