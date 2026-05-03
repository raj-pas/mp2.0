/**
 * Session-interruption recovery for the doc-drop upload flow
 * (Phase 5b.8). When an upload fails with 401 mid-flight (e.g.
 * session expired during a long Bedrock-bound real-PII upload),
 * stash a draft so the advisor doesn't have to retype the workspace
 * label or guess which files were attempted.
 *
 * What we CAN preserve in sessionStorage: label, data_origin, file
 * metadata (name + size). What we CANNOT preserve: the actual File
 * blob bytes — those are opaque to JSON. Advisor must re-pick the
 * files. The metadata list lets the advisor verify they're picking
 * the same files they originally dropped.
 *
 * Drafts expire after 30 minutes to avoid stale state cluttering
 * the next session's first paint of /review.
 */

import type { DataOrigin } from "./review";

const STORAGE_KEY = "mp20.upload-draft.v1";
const TTL_MS = 30 * 60 * 1000;

export type UploadFileMeta = {
  name: string;
  size: number;
};

export type UploadDraft = {
  label: string;
  data_origin: DataOrigin;
  files: UploadFileMeta[];
  saved_at: number;
  /**
   * Set when the workspace was created server-side before the 401
   * fired (i.e., create succeeded, upload failed). On resume the
   * upload is retargeted at this existing workspace — the SHA256
   * dedup in the upload endpoint makes this safe even if some
   * files succeeded before the 401. Absent when create itself
   * 401'd; resume creates a fresh workspace in that case.
   */
  workspace_id?: string;
};

function storage(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

export function saveUploadDraft(input: {
  label: string;
  data_origin: DataOrigin;
  files: File[] | UploadFileMeta[];
  workspace_id?: string;
}): void {
  const store = storage();
  if (store === null) return;
  const fileMeta: UploadFileMeta[] = input.files.map((f) => ({
    name: f.name,
    size: f.size,
  }));
  const payload: UploadDraft = {
    label: input.label,
    data_origin: input.data_origin,
    files: fileMeta,
    saved_at: Date.now(),
    ...(input.workspace_id !== undefined ? { workspace_id: input.workspace_id } : {}),
  };
  store.setItem(STORAGE_KEY, JSON.stringify(payload));
}

function readDraft(): UploadDraft | null {
  const store = storage();
  if (store === null) return null;
  const raw = store.getItem(STORAGE_KEY);
  if (raw === null) return null;
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    store.removeItem(STORAGE_KEY);
    return null;
  }
  if (
    typeof parsed !== "object" ||
    parsed === null ||
    typeof (parsed as UploadDraft).label !== "string" ||
    typeof (parsed as UploadDraft).saved_at !== "number" ||
    !Array.isArray((parsed as UploadDraft).files)
  ) {
    store.removeItem(STORAGE_KEY);
    return null;
  }
  const draft = parsed as UploadDraft;
  if (Date.now() - draft.saved_at > TTL_MS) {
    store.removeItem(STORAGE_KEY);
    return null;
  }
  return draft;
}

/**
 * Returns the saved draft (if any). Does NOT clear sessionStorage
 * — use when the caller wants to detect-and-redirect, then let
 * the destination consumer call `consumeUploadDraft`.
 */
export function peekUploadDraft(): UploadDraft | null {
  return readDraft();
}

/**
 * Returns the saved draft (if any) and removes it from
 * sessionStorage so it's only restored once.
 */
export function consumeUploadDraft(): UploadDraft | null {
  const draft = readDraft();
  if (draft !== null) {
    storage()?.removeItem(STORAGE_KEY);
  }
  return draft;
}

export function clearUploadDraft(): void {
  storage()?.removeItem(STORAGE_KEY);
}
