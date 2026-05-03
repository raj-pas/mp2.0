/**
 * Vitest scaffolding test (Phase 6 scaffolding — sub-session #3).
 *
 * Verifies the new Vitest + jsdom setup works end-to-end against
 * a small pure module (`lib/upload-recovery.ts`). Phase 6 (sub-
 * session #4) layers in the full property + boundary + edge-case
 * suites; this scaffolding test exists primarily to confirm the
 * test runner + sessionStorage shim + module resolution all wire
 * up correctly.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  clearUploadDraft,
  consumeUploadDraft,
  peekUploadDraft,
  saveUploadDraft,
} from "../upload-recovery";

describe("upload-recovery", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  afterEach(() => {
    window.sessionStorage.clear();
    vi.useRealTimers();
  });

  it("saves and consumes a draft round-trip", () => {
    saveUploadDraft({
      label: "Niesner onboarding",
      data_origin: "real_derived",
      files: [
        { name: "kyc.pdf", size: 1024 },
        { name: "statement.pdf", size: 2048 },
      ],
    });

    const draft = consumeUploadDraft();
    expect(draft).not.toBeNull();
    expect(draft?.label).toBe("Niesner onboarding");
    expect(draft?.data_origin).toBe("real_derived");
    expect(draft?.files).toHaveLength(2);
    expect(draft?.files[0]?.name).toBe("kyc.pdf");

    // consume is one-shot — second call is null.
    expect(consumeUploadDraft()).toBeNull();
  });

  it("preserves workspace_id when supplied", () => {
    saveUploadDraft({
      label: "WS",
      data_origin: "synthetic",
      files: [{ name: "a.pdf", size: 100 }],
      workspace_id: "00000000-aaaa-bbbb-cccc-000000000001",
    });
    const draft = consumeUploadDraft();
    expect(draft?.workspace_id).toBe("00000000-aaaa-bbbb-cccc-000000000001");
  });

  it("expires drafts after 30 minutes (TTL_MS boundary)", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-05-03T12:00:00Z"));
    saveUploadDraft({
      label: "Expired",
      data_origin: "synthetic",
      files: [],
    });
    // Advance just past 30 minutes
    vi.setSystemTime(new Date("2026-05-03T12:30:01Z"));
    expect(consumeUploadDraft()).toBeNull();
  });

  it("preserves drafts inside the TTL window", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-05-03T12:00:00Z"));
    saveUploadDraft({
      label: "Fresh",
      data_origin: "synthetic",
      files: [],
    });
    vi.setSystemTime(new Date("2026-05-03T12:29:59Z"));
    expect(consumeUploadDraft()?.label).toBe("Fresh");
  });

  it("peek does NOT clear the draft", () => {
    saveUploadDraft({
      label: "Peek-test",
      data_origin: "synthetic",
      files: [],
    });
    expect(peekUploadDraft()?.label).toBe("Peek-test");
    // Still there
    expect(peekUploadDraft()?.label).toBe("Peek-test");
    expect(consumeUploadDraft()?.label).toBe("Peek-test");
    expect(peekUploadDraft()).toBeNull();
  });

  it("clear removes the draft", () => {
    saveUploadDraft({
      label: "Clear-test",
      data_origin: "synthetic",
      files: [],
    });
    clearUploadDraft();
    expect(peekUploadDraft()).toBeNull();
  });

  it("tolerates malformed sessionStorage JSON without throwing", () => {
    window.sessionStorage.setItem("mp20.upload-draft.v1", "{not valid JSON");
    expect(peekUploadDraft()).toBeNull();
    // Auto-cleared after a malformed read so future saves don't
    // tangle with the bad row.
    expect(window.sessionStorage.getItem("mp20.upload-draft.v1")).toBeNull();
  });

  it("tolerates structurally-invalid stored drafts", () => {
    // Missing required fields (label, files, saved_at)
    window.sessionStorage.setItem(
      "mp20.upload-draft.v1",
      JSON.stringify({ data_origin: "synthetic" }),
    );
    expect(peekUploadDraft()).toBeNull();
  });
});
