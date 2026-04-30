/**
 * Wizard draft persistence + state recovery (locked decision #35).
 *
 * Draft state is keyed by a per-tab session id so multi-tab edits
 * don't collide. The id lives in `sessionStorage` (cleared on tab
 * close); the draft itself lives in `localStorage` so a crash
 * recovers cleanly. Recovery prompt fires when a non-empty draft is
 * present at wizard mount time.
 *
 * Per locked decision #35, draft inputs are NOT real PII until
 * commit; the user can discard explicitly. Wizard-name fields are
 * synthetic until the household tree is created in the DB.
 */
import { useEffect, useMemo, useState } from "react";

import { type WizardDraft, emptyWizardDraft } from "./schema";

const SESSION_KEY = "mp20_wizard_session";
const DRAFT_KEY_PREFIX = "mp20_wizard_draft_";
const HEARTBEAT_MS = 30_000;

function getOrCreateSessionId(): string {
  if (typeof window === "undefined") return "_ssr";
  const existing = window.sessionStorage.getItem(SESSION_KEY);
  if (existing !== null && existing.length > 0) return existing;
  const fresh = `wiz_${Date.now()}_${Math.floor(Math.random() * 1e6)}`;
  window.sessionStorage.setItem(SESSION_KEY, fresh);
  return fresh;
}

function draftKey(sessionId: string): string {
  return `${DRAFT_KEY_PREFIX}${sessionId}`;
}

export type DraftStatus = "fresh" | "resumable";

export interface WizardDraftStore {
  sessionId: string;
  status: DraftStatus;
  initialDraft: WizardDraft;
  saveDraft: (draft: WizardDraft) => void;
  clearDraft: () => void;
}

/**
 * One-shot driver — call at wizard mount. Returns the draft that
 * should hydrate the form. Subsequent saves come via `saveDraft`.
 *
 * The hook intentionally does not subscribe to localStorage updates
 * (unlike `useLocalStorage`) — within one tab the wizard is the only
 * writer.
 */
export function useWizardDraftStore(): WizardDraftStore {
  const sessionId = useMemo(getOrCreateSessionId, []);
  const [{ status, initialDraft }] = useState(() => loadInitial(sessionId));

  function saveDraft(draft: WizardDraft) {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem(draftKey(sessionId), JSON.stringify(draft));
    } catch {
      // best-effort persistence
    }
  }

  function clearDraft() {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.removeItem(draftKey(sessionId));
    } catch {
      // ignore
    }
  }

  return { sessionId, status, initialDraft, saveDraft, clearDraft };
}

function loadInitial(sessionId: string): {
  status: DraftStatus;
  initialDraft: WizardDraft;
} {
  if (typeof window === "undefined") {
    return { status: "fresh", initialDraft: emptyWizardDraft() };
  }
  try {
    const raw = window.localStorage.getItem(draftKey(sessionId));
    if (raw === null) return { status: "fresh", initialDraft: emptyWizardDraft() };
    const parsed = JSON.parse(raw) as WizardDraft;
    if (isMeaningfulDraft(parsed)) {
      return { status: "resumable", initialDraft: parsed };
    }
    return { status: "fresh", initialDraft: emptyWizardDraft() };
  } catch {
    return { status: "fresh", initialDraft: emptyWizardDraft() };
  }
}

function isMeaningfulDraft(draft: WizardDraft): boolean {
  return (
    draft.display_name.trim().length > 0 ||
    draft.notes.trim().length > 0 ||
    draft.members.some((m) => m.name.trim().length > 0 || m.dob.trim().length > 0) ||
    draft.accounts.some((a) => a.current_value.trim().length > 0) ||
    draft.goals.some((g) => g.name.trim().length > 0)
  );
}

/**
 * 30-second heartbeat — periodic persistence so even mid-step churn
 * is recoverable. Wire this in the wizard root.
 */
export function useDraftHeartbeat(snapshot: () => WizardDraft, save: (draft: WizardDraft) => void) {
  useEffect(() => {
    const id = window.setInterval(() => {
      save(snapshot());
    }, HEARTBEAT_MS);
    return () => window.clearInterval(id);
  }, [snapshot, save]);
}
