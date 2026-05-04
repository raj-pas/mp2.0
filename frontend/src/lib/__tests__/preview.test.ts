/**
 * preview.ts — `useGeneratePortfolio` mutation hook unit tests
 * (sub-session #4 R1, locked #106).
 *
 * Verifies:
 *   - URL: POST /api/clients/<id>/generate-portfolio/
 *   - body: empty {} object (engine derives all inputs server-side)
 *   - onSuccess: invalidates ["household", id] + fires toastSuccess
 *   - onError:   fires toastError with the normalized message
 *   - isPending: reflects in-flight state
 *
 * Mocks `apiFetch` (so we don't hit the network) and `../toast`. Wraps the
 * hook in a fresh QueryClient per test (React Testing Library renderHook
 * pattern, mirroring WelcomeTour.test.tsx's QueryClientProvider usage).
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.fn();
vi.mock("../api", () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  ApiError: class ApiError extends Error {
    status: number;
    body: unknown;
    constructor(status: number, body: unknown, message: string) {
      super(message);
      this.status = status;
      this.body = body;
    }
  },
}));

const toastSuccessMock = vi.fn();
const toastErrorMock = vi.fn();
vi.mock("../toast", () => ({
  toastSuccess: (...args: unknown[]) => toastSuccessMock(...args),
  toastError: (...args: unknown[]) => toastErrorMock(...args),
  toastInfo: vi.fn(),
}));

// Import AFTER mocks so the hook resolves the mocked api/toast modules.
import { useGeneratePortfolio } from "../preview";
import { householdQueryKey } from "../household";

function makeWrapper(client: QueryClient) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client }, children);
  };
}

beforeEach(() => {
  apiFetchMock.mockReset();
  toastSuccessMock.mockClear();
  toastErrorMock.mockClear();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("useGeneratePortfolio", () => {
  it("POSTs to /api/clients/<id>/generate-portfolio/ with empty body", async () => {
    apiFetchMock.mockResolvedValue({ id: 1, run_signature: "sig" });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    const { result } = renderHook(() => useGeneratePortfolio("hh_test"), {
      wrapper: makeWrapper(client),
    });

    await act(async () => {
      result.current.mutate();
    });

    await waitFor(() => expect(apiFetchMock).toHaveBeenCalledTimes(1));
    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/clients/hh_test/generate-portfolio/",
      { method: "POST", body: {} },
    );
  });

  it("URL-encodes the householdId", async () => {
    apiFetchMock.mockResolvedValue({ id: 1, run_signature: "sig" });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    const { result } = renderHook(
      () => useGeneratePortfolio("hh client/with spaces"),
      { wrapper: makeWrapper(client) },
    );

    await act(async () => {
      result.current.mutate();
    });

    await waitFor(() => expect(apiFetchMock).toHaveBeenCalledTimes(1));
    expect(apiFetchMock.mock.calls[0]?.[0]).toBe(
      "/api/clients/hh%20client%2Fwith%20spaces/generate-portfolio/",
    );
  });

  it("rejects when householdId is null (does not call apiFetch)", async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    const { result } = renderHook(() => useGeneratePortfolio(null), {
      wrapper: makeWrapper(client),
    });

    await act(async () => {
      result.current.mutate();
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(apiFetchMock).not.toHaveBeenCalled();
    expect(result.current.error?.message).toMatch(/household id required/);
  });

  it("onSuccess invalidates the household query key + fires toastSuccess", async () => {
    apiFetchMock.mockResolvedValue({
      id: 2,
      run_signature: "sig123",
      external_id: "ext",
    });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    const invalidateSpy = vi.spyOn(client, "invalidateQueries");

    const { result } = renderHook(() => useGeneratePortfolio("hh_sandra"), {
      wrapper: makeWrapper(client),
    });

    await act(async () => {
      result.current.mutate();
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: householdQueryKey("hh_sandra"),
    });
    expect(toastSuccessMock).toHaveBeenCalledWith("Recommendation refreshed.");
  });

  it("onError fires toastError with the rejection message", async () => {
    apiFetchMock.mockRejectedValue(new Error("Network down"));
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    const { result } = renderHook(() => useGeneratePortfolio("hh_sandra"), {
      wrapper: makeWrapper(client),
    });

    await act(async () => {
      result.current.mutate();
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(toastErrorMock).toHaveBeenCalledWith(
      "Couldn't refresh recommendation.",
      { description: "Network down" },
    );
    expect(toastSuccessMock).not.toHaveBeenCalled();
  });

  it("isPending is true while the mutation is in flight, false after success", async () => {
    let resolveFetch: (v: unknown) => void = () => {};
    apiFetchMock.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveFetch = resolve;
        }),
    );
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    const { result } = renderHook(() => useGeneratePortfolio("hh_sandra"), {
      wrapper: makeWrapper(client),
    });

    expect(result.current.isPending).toBe(false);

    act(() => {
      result.current.mutate();
    });

    await waitFor(() => expect(result.current.isPending).toBe(true));

    await act(async () => {
      resolveFetch({ id: 1, run_signature: "sig" });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.isPending).toBe(false);
  });

  it("does NOT invalidate or toast on failure", async () => {
    apiFetchMock.mockRejectedValue(new Error("boom"));
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    const invalidateSpy = vi.spyOn(client, "invalidateQueries");

    const { result } = renderHook(() => useGeneratePortfolio("hh_sandra"), {
      wrapper: makeWrapper(client),
    });

    await act(async () => {
      result.current.mutate();
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(invalidateSpy).not.toHaveBeenCalled();
    expect(toastSuccessMock).not.toHaveBeenCalled();
  });
});
