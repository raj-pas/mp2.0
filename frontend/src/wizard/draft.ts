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
const DRAFT_META_KEY_PREFIX = "mp20_wizard_draft_meta_";
const HEARTBEAT_MS = 30_000;

interface DraftMeta {
  saved_at: string; // ISO 8601 timestamp
}

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

function draftMetaKey(sessionId: string): string {
  return `${DRAFT_META_KEY_PREFIX}${sessionId}`;
}

export type DraftStatus = "fresh" | "resumable";

export interface WizardDraftStore {
  sessionId: string;
  status: DraftStatus;
  initialDraft: WizardDraft;
  initialSavedAt: string | null;
  saveDraft: (draft: WizardDraft) => string;
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
  const [{ status, initialDraft, initialSavedAt }] = useState(() => loadInitial(sessionId));

  function saveDraft(draft: WizardDraft): string {
    const savedAt = new Date().toISOString();
    if (typeof window === "undefined") return savedAt;
    try {
      window.localStorage.setItem(draftKey(sessionId), JSON.stringify(draft));
      const meta: DraftMeta = { saved_at: savedAt };
      window.localStorage.setItem(draftMetaKey(sessionId), JSON.stringify(meta));
    } catch {
      // best-effort persistence
    }
    return savedAt;
  }

  function clearDraft() {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.removeItem(draftKey(sessionId));
      window.localStorage.removeItem(draftMetaKey(sessionId));
    } catch {
      // ignore
    }
  }

  return { sessionId, status, initialDraft, initialSavedAt, saveDraft, clearDraft };
}

function loadInitial(sessionId: string): {
  status: DraftStatus;
  initialDraft: WizardDraft;
  initialSavedAt: string | null;
} {
  if (typeof window === "undefined") {
    return { status: "fresh", initialDraft: emptyWizardDraft(), initialSavedAt: null };
  }
  try {
    const raw = window.localStorage.getItem(draftKey(sessionId));
    if (raw === null)
      return { status: "fresh", initialDraft: emptyWizardDraft(), initialSavedAt: null };
    const parsed = JSON.parse(raw) as WizardDraft;
    if (isMeaningfulDraft(parsed)) {
      let savedAt: string | null = null;
      try {
        const metaRaw = window.localStorage.getItem(draftMetaKey(sessionId));
        if (metaRaw !== null) {
          const meta = JSON.parse(metaRaw) as DraftMeta;
          if (typeof meta.saved_at === "string") savedAt = meta.saved_at;
        }
      } catch {
        // meta is best-effort; absence is non-fatal
      }
      return { status: "resumable", initialDraft: parsed, initialSavedAt: savedAt };
    }
    return { status: "fresh", initialDraft: emptyWizardDraft(), initialSavedAt: null };
  } catch {
    return { status: "fresh", initialDraft: emptyWizardDraft(), initialSavedAt: null };
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
