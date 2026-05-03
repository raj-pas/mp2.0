/**
 * Tier 3 polish coverage — wizard draft store (§1.8 save-as-draft).
 *
 * Verifies the localStorage round-trip + the new `_meta_` ISO
 * timestamp pattern that the save-as-draft button surfaces in the
 * resume banner.
 */
import { renderHook, act } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { emptyWizardDraft } from "../schema";
import { useWizardDraftStore } from "../draft";

beforeEach(() => {
  window.sessionStorage.clear();
  window.localStorage.clear();
});

afterEach(() => {
  window.sessionStorage.clear();
  window.localStorage.clear();
});

describe("useWizardDraftStore", () => {
  it("starts in fresh state when no draft exists", () => {
    const { result } = renderHook(() => useWizardDraftStore());
    expect(result.current.status).toBe("fresh");
    expect(result.current.initialSavedAt).toBeNull();
  });

  it("saveDraft returns an ISO timestamp + persists meta", () => {
    const { result } = renderHook(() => useWizardDraftStore());
    let savedAt = "";
    act(() => {
      const draft = emptyWizardDraft();
      draft.display_name = "Pilot Test Household";
      savedAt = result.current.saveDraft(draft);
    });
    expect(savedAt).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    // Meta key is keyed off session id — find the matching key
    const sessionKey = window.sessionStorage.getItem("mp20_wizard_session");
    expect(sessionKey).toBeTruthy();
    const metaRaw = window.localStorage.getItem(`mp20_wizard_draft_meta_${sessionKey}`);
    expect(metaRaw).toBeTruthy();
    const meta = JSON.parse(metaRaw ?? "{}");
    expect(meta.saved_at).toBe(savedAt);
  });

  it("clearDraft removes both draft + meta entries", () => {
    const { result } = renderHook(() => useWizardDraftStore());
    act(() => {
      const draft = emptyWizardDraft();
      draft.display_name = "Pilot Test Household";
      result.current.saveDraft(draft);
    });
    const sessionKey = window.sessionStorage.getItem("mp20_wizard_session");
    expect(window.localStorage.getItem(`mp20_wizard_draft_${sessionKey}`)).toBeTruthy();
    act(() => {
      result.current.clearDraft();
    });
    expect(window.localStorage.getItem(`mp20_wizard_draft_${sessionKey}`)).toBeNull();
    expect(window.localStorage.getItem(`mp20_wizard_draft_meta_${sessionKey}`)).toBeNull();
  });

  it("loadInitial surfaces saved meta as initialSavedAt on resumable mount", () => {
    // Pre-populate localStorage as if a previous session saved a draft.
    const sessionId = "wiz_test_1";
    window.sessionStorage.setItem("mp20_wizard_session", sessionId);
    const draft = emptyWizardDraft();
    draft.display_name = "Resumable Household";
    window.localStorage.setItem(`mp20_wizard_draft_${sessionId}`, JSON.stringify(draft));
    window.localStorage.setItem(
      `mp20_wizard_draft_meta_${sessionId}`,
      JSON.stringify({ saved_at: "2026-05-03T15:00:00.000Z" }),
    );

    const { result } = renderHook(() => useWizardDraftStore());
    expect(result.current.status).toBe("resumable");
    expect(result.current.initialDraft.display_name).toBe("Resumable Household");
    expect(result.current.initialSavedAt).toBe("2026-05-03T15:00:00.000Z");
  });

  it("treats meaningless draft (all empty) as fresh on mount", () => {
    const sessionId = "wiz_test_2";
    window.sessionStorage.setItem("mp20_wizard_session", sessionId);
    window.localStorage.setItem(
      `mp20_wizard_draft_${sessionId}`,
      JSON.stringify(emptyWizardDraft()),
    );
    const { result } = renderHook(() => useWizardDraftStore());
    expect(result.current.status).toBe("fresh");
  });
});
