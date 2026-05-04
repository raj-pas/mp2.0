/**
 * DocDropOverlay unit tests — pin the StrictMode-double-update fix
 * for `admitFiles` (regression caught by foundation R7 e2e on
 * 2026-05-03 after Tier 3 polish bundle B).
 *
 * Why pin it here: React 18 StrictMode invokes setState updaters
 * twice in dev to surface impurities. Tier 3's earlier
 * `admitFiles` rewrote pushed into closure-captured arrays inside
 * the updater, so a single dropped file produced TWO entries.
 * The fix moves dedup + classification OUTSIDE the updater + uses
 * a pure spread; this test mounts the component inside StrictMode
 * and confirms the file count stays at exactly 1 for one input.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { StrictMode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DocDropOverlay } from "../DocDropOverlay";

const createWorkspaceMutate = vi.fn();
const uploadMutate = vi.fn();

vi.mock("../../lib/review", () => ({
  useCreateWorkspace: () => ({
    mutateAsync: createWorkspaceMutate,
    isPending: false,
  }),
  useUploadDocuments: () => ({
    mutateAsync: uploadMutate,
    isPending: false,
  }),
}));
vi.mock("../../lib/toast", () => ({
  toastError: vi.fn(),
  toastSuccess: vi.fn(),
}));
vi.mock("@tanstack/react-query", async () => {
  const actual = await vi.importActual<typeof import("@tanstack/react-query")>(
    "@tanstack/react-query",
  );
  return {
    ...actual,
    useQueryClient: () => ({ invalidateQueries: vi.fn() }),
  };
});

afterEach(() => {
  createWorkspaceMutate.mockClear();
  uploadMutate.mockClear();
  window.sessionStorage.clear();
});

describe("DocDropOverlay admitFiles + StrictMode", () => {
  function fireFileChange(input: HTMLInputElement, files: File[]) {
    // jsdom's input.files is non-configurable after first set, so use
    // fireEvent.change with the target.files override pattern.
    fireEvent.change(input, { target: { files } });
  }

  it("registers exactly one file when one input is provided (StrictMode-safe)", () => {
    // StrictMode invokes setState updaters twice in dev; if admitFiles
    // pushes into a closure-captured `accepted` array inside the
    // setFiles updater, the file would double. The fix computes
    // accepted OUTSIDE the updater + passes it to a pure spread.
    render(
      <StrictMode>
        <DocDropOverlay onWorkspaceReady={() => {}} />
      </StrictMode>,
    );

    // Find the hidden file input + simulate selecting one file.
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput).toBeTruthy();

    const file = new File(["x".repeat(100)], "smoke.txt", { type: "text/plain" });
    fireFileChange(fileInput, [file]);

    // Exactly one row in the picker — not two (the StrictMode
    // double-update regression would produce two).
    const fileRows = screen.getAllByText(/smoke\.txt/);
    expect(fileRows.length).toBe(1);
  });

  it("dedups identical files across consecutive drops", () => {
    render(
      <StrictMode>
        <DocDropOverlay onWorkspaceReady={() => {}} />
      </StrictMode>,
    );
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["x".repeat(100)], "dup.txt", { type: "text/plain" });
    fireFileChange(fileInput, [file]);
    // Re-trigger with the same file (same name + size key).
    fireFileChange(fileInput, [file]);

    // Still only one row — the second drop is dedup'd against the
    // first via the (name + size) key.
    const fileRows = screen.getAllByText(/dup\.txt/);
    expect(fileRows.length).toBe(1);
  });

  it("rejects files exceeding MAX_FILE_BYTES (50MB)", () => {
    render(
      <StrictMode>
        <DocDropOverlay onWorkspaceReady={() => {}} />
      </StrictMode>,
    );
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    // jsdom's File constructor doesn't store size accurately; override
    // explicitly so admitFiles' size cap path triggers.
    const large = new File(["x"], "big.pdf", { type: "application/pdf" });
    Object.defineProperty(large, "size", { value: 60 * 1024 * 1024 });
    fireFileChange(fileInput, [large]);

    // The file row should NOT appear.
    expect(screen.queryByText(/big\.pdf/)).toBeNull();
  });
});
