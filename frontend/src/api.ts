import type { EngineOutput, HouseholdDetail, HouseholdSummary } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

export function fetchClients(): Promise<HouseholdSummary[]> {
  return request<HouseholdSummary[]>("/api/clients/");
}

export function fetchClient(id: string): Promise<HouseholdDetail> {
  return request<HouseholdDetail>(`/api/clients/${id}/`);
}

export function generatePortfolio(id: string): Promise<EngineOutput> {
  return request<EngineOutput>(`/api/clients/${id}/generate-portfolio/`, {
    method: "POST",
  });
}
