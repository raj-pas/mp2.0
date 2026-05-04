/**
 * Multi-file drop zone for the v36 doc-drop entry (canon §6.7,
 * locked decision #7 — primary onboarding path).
 *
 * Two-step flow:
 *   1. Advisor types a workspace label + selects/drags files.
 *   2. Click "Start review" — creates a workspace, uploads all files
 *      in one multipart POST, opens the new workspace in the parent
 *      ReviewScreen so the advisor can watch processing live.
 *
 * Real-PII discipline (canon §11.8.3): the secure-root validation
 * happens server-side. For `data_origin: real_derived` the upload
 * fails with 503 if `MP20_SECURE_DATA_ROOT` is missing or in-repo.
 * Synthetic uploads bypass the gate (R7 dev iterates against
 * synthetic).
 */
import { Upload, X } from "lucide-react";
import { type ChangeEvent, type DragEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";

import { Button } from "../components/ui/button";
import { useCreateWorkspace, useUploadDocuments } from "../lib/review";
import { isAuthError, normalizeApiError } from "../lib/api-error";
import { SESSION_QUERY_KEY } from "../lib/auth";
import { toastError, toastSuccess } from "../lib/toast";
import { cn } from "../lib/cn";
import {
  clearUploadDraft,
  consumeUploadDraft,
  saveUploadDraft,
  type UploadFileMeta,
} from "../lib/upload-recovery";

/**
 * Per-file upload size cap. Real-PII PDFs cap at ~20MB in practice;
 * 50MB gives headroom for scan-quality statements without blowing
 * the gunicorn worker timeout. Larger files are rejected client-
 * side with a clear toast + per-file ignored entry, mirroring the
 * server's per-file partial-failure pattern.
 */
const MAX_FILE_BYTES = 50 * 1024 * 1024;

interface DocDropOverlayProps {
  /** Called with the new workspace external_id once create + upload succeed. */
  onWorkspaceReady: (workspaceId: string) => void;
}

interface IgnoredPickEntry {
  filename: string;
  reason: "too_large" | "duplicate";
  size: number;
}

export function DocDropOverlay({ onWorkspaceReady }: DocDropOverlayProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [label, setLabel] = useState("");
  const [dataOrigin, setDataOrigin] = useState<"real_derived" | "synthetic">("synthetic");
  const [files, setFiles] = useState<File[]>([]);
  const [pendingFileMeta, setPendingFileMeta] = useState<UploadFileMeta[]>([]);
  const [pendingWorkspaceId, setPendingWorkspaceId] = useState<string | null>(null);
  // Files that the server reported as upload_failed in the prior
  // attempt — retained so the advisor can retry just the failed
  // subset without re-picking everything.
  const [retryableFiles, setRetryableFiles] = useState<File[]>([]);
  const [retryWorkspaceId, setRetryWorkspaceId] = useState<string | null>(null);
  const [isDragOver, setDragOver] = useState(false);

  const createWorkspace = useCreateWorkspace();
  const upload = useUploadDocuments();

  // Phase 5b.8: restore an upload draft if a prior attempt was
  // interrupted by a 401. We can preserve label + data_origin +
  // file metadata + (optionally) workspace_id, but not the File
  // bytes — browsers don't expose them across sessionStorage. The
  // pendingFileMeta state shows the advisor which files they
  // originally dropped so they can re-pick the same set.
  // The pendingWorkspaceId routes resume uploads at the existing
  // workspace (avoiding orphan-workspace leaks; see handoff
  // 2026-05-03 for the deep design analysis: D + E option).
  useEffect(() => {
    const draft = consumeUploadDraft();
    if (draft === null) return;
    setLabel(draft.label);
    setDataOrigin(draft.data_origin);
    setPendingFileMeta(draft.files);
    if (draft.workspace_id !== undefined) {
      setPendingWorkspaceId(draft.workspace_id);
    }
    toastSuccess(
      t("docdrop.draft_restored_title"),
      t("docdrop.draft_restored_body", {
        count: draft.files.length,
        label: draft.label,
      }),
    );
  }, [t]);

  function admitFiles(incoming: File[]) {
    if (incoming.length === 0) return;
    // CRITICAL — do not mutate closure-captured arrays inside the
    // setFiles updater. React 18 StrictMode invokes the updater
    // twice in dev to surface impurities, and any push() into an
    // outer-scope `accepted`/`ignored` would double-count (same
    // FileList-race class from R7 history, regressed by Tier 3
    // polish bundle B in this session and surfaced by foundation
    // R7 e2e on 2026-05-03).
    //
    // Pattern: classify against the at-call-time `files` snapshot
    // (closure-captured in the function scope, not the updater),
    // produce immutable `accepted` + `ignored` lists, then pass
    // the pure `accepted` list into the updater.
    const seen = new Set(files.map((f) => `${f.name}::${f.size}`));
    const accepted: File[] = [];
    const ignored: IgnoredPickEntry[] = [];
    for (const file of incoming) {
      const key = `${file.name}::${file.size}`;
      if (seen.has(key)) {
        ignored.push({ filename: file.name, reason: "duplicate", size: file.size });
        continue;
      }
      if (file.size > MAX_FILE_BYTES) {
        ignored.push({ filename: file.name, reason: "too_large", size: file.size });
        continue;
      }
      seen.add(key);
      accepted.push(file);
    }
    if (accepted.length > 0) {
      setFiles((prev) => [...prev, ...accepted]);
    }
    if (ignored.length > 0) {
      const tooLarge = ignored.filter((e) => e.reason === "too_large");
      const duplicates = ignored.filter((e) => e.reason === "duplicate");
      if (tooLarge.length > 0) {
        toastError(t("docdrop.too_large_title"), {
          description: t("docdrop.too_large_body", {
            count: tooLarge.length,
            names: tooLarge.map((e) => e.filename).join(", "),
            limit_mb: Math.round(MAX_FILE_BYTES / (1024 * 1024)),
          }),
        });
      }
      if (duplicates.length > 0) {
        toastSuccess(
          t("docdrop.duplicate_title"),
          t("docdrop.duplicate_body", {
            count: duplicates.length,
            names: duplicates.map((e) => e.filename).join(", "),
          }),
        );
      }
    }
  }

  function handleFilesPicked(event: ChangeEvent<HTMLInputElement>) {
    // FileList from `event.target.files` is a LIVE reference: clearing
    // `event.target.value` empties it, which races against React's
    // deferred setFiles callback. Snapshot to a plain array BEFORE
    // clearing the input so the callback sees stable data.
    const picked = event.target.files;
    if (picked === null || picked.length === 0) return;
    const snapshot = Array.from(picked);
    event.target.value = "";
    admitFiles(snapshot);
    // The advisor is re-picking files; the recovered metadata list
    // is no longer needed as a hint.
    if (pendingFileMeta.length > 0) setPendingFileMeta([]);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragOver(false);
    const dropped = event.dataTransfer.files;
    if (dropped.length === 0) return;
    // Same snapshot discipline — DataTransfer.files is also live.
    const snapshot = Array.from(dropped);
    admitFiles(snapshot);
    if (pendingFileMeta.length > 0) setPendingFileMeta([]);
  }

  function removeFile(index: number) {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }

  function discardDraft() {
    setLabel("");
    setDataOrigin("synthetic");
    setPendingFileMeta([]);
    setPendingWorkspaceId(null);
    setRetryableFiles([]);
    setRetryWorkspaceId(null);
    clearUploadDraft();
  }

  function bounceToLogin() {
    toastError(t("docdrop.session_expired_title"), {
      description: t("docdrop.session_expired_body"),
    });
    queryClient.invalidateQueries({ queryKey: SESSION_QUERY_KEY });
  }

  function handleUploadSuccess(
    workspaceId: string,
    sourceFiles: File[],
    response: { uploaded: { document_id: number }[]; ignored: { reason: string; filename: string }[] },
  ) {
    // Resume succeeded — clear the draft so a future re-mount of
    // DocDropOverlay doesn't restore stale state.
    clearUploadDraft();
    setPendingWorkspaceId(null);
    setPendingFileMeta([]);

    const failedFilenames = new Set(
      response.ignored
        .filter((row) => row.reason === "upload_failed")
        .map((row) => row.filename),
    );
    // Retain the actual File objects for failed uploads so the
    // advisor can retry the failed subset without re-picking. Match
    // by filename — the server doesn't echo size in `ignored`, but
    // filename is unique within a single upload batch (the SHA256
    // dedup runs server-side).
    const retryable = sourceFiles.filter((f) => failedFilenames.has(f.name));

    if (response.uploaded.length === 0) {
      // Total failure — keep files in the picker so advisor can
      // adjust + try again. Don't navigate away.
      setRetryableFiles(retryable);
      setRetryWorkspaceId(workspaceId);
      toastError(t("docdrop.upload_error"), {
        description: t("docdrop.upload_all_failed", {
          count: failedFilenames.size,
        }),
      });
      return;
    }
    if (failedFilenames.size > 0) {
      // Partial — surface the retry-failed CTA + navigate to the
      // workspace so advisor can monitor the docs that DID land.
      setRetryableFiles(retryable);
      setRetryWorkspaceId(workspaceId);
      toastSuccess(
        t("docdrop.upload_partial_title"),
        t("docdrop.upload_partial_body", {
          uploaded: response.uploaded.length,
          failed: failedFilenames.size,
          names: Array.from(failedFilenames).join(", "),
        }),
      );
    } else {
      setRetryableFiles([]);
      setRetryWorkspaceId(null);
      toastSuccess(t("docdrop.upload_success_title"), t("docdrop.upload_success_body"));
    }
    onWorkspaceReady(workspaceId);
    setLabel("");
    setFiles([]);
  }

  function retryFailedFiles() {
    if (retryableFiles.length === 0 || retryWorkspaceId === null) return;
    const target = retryWorkspaceId;
    const filesToRetry = retryableFiles;
    upload.mutate(
      { workspaceId: target, files: filesToRetry },
      {
        onSuccess: (response) => handleUploadSuccess(target, filesToRetry, response),
        onError: (err) => {
          const e = normalizeApiError(err, t("docdrop.upload_error"));
          if (isAuthError(e)) {
            // Stash the failed-files context as if it were a draft
            // recovery scenario. Mirrors handleStart's E timing.
            saveUploadDraft({
              label: label.trim() || "Retry failed",
              data_origin: dataOrigin,
              files: filesToRetry,
              workspace_id: target,
            });
            bounceToLogin();
            return;
          }
          toastError(t("docdrop.upload_error"), { description: e.message });
        },
      },
    );
  }

  function executeUpload(workspaceId: string, allowCreateFallback: boolean) {
    const filesSnapshot = files;
    upload.mutate(
      { workspaceId, files: filesSnapshot },
      {
        onSuccess: (response) => handleUploadSuccess(workspaceId, filesSnapshot, response),
        onError: (err) => {
          const e = normalizeApiError(err, t("docdrop.upload_error"));
          if (isAuthError(e)) {
            // Draft was already stashed at handleStart; just bounce.
            bounceToLogin();
            return;
          }
          if (e.status === 404 && allowCreateFallback) {
            // Stale workspace_id (server-side state divergence: the
            // workspace was deleted, or _workspace_for_user no longer
            // owns it). Fall through to a fresh create + upload —
            // the SHA256 dedup in the upload endpoint makes this
            // safe even if some original files already existed
            // somewhere we can't see.
            setPendingWorkspaceId(null);
            saveUploadDraft({
              label: label.trim(),
              data_origin: dataOrigin,
              files,
            });
            executeCreateThenUpload();
            return;
          }
          toastError(t("docdrop.upload_error"), { description: e.message });
        },
      },
    );
  }

  function executeCreateThenUpload() {
    createWorkspace.mutate(
      { label: label.trim(), data_origin: dataOrigin },
      {
        onSuccess: (workspace) => {
          // Re-stash with workspace_id so a 401 mid-upload doesn't
          // leak the just-created workspace as an orphan.
          saveUploadDraft({
            label: label.trim(),
            data_origin: dataOrigin,
            files,
            workspace_id: workspace.external_id,
          });
          executeUpload(workspace.external_id, false);
        },
        onError: (err) => {
          const e = normalizeApiError(err, t("docdrop.create_error"));
          if (isAuthError(e)) {
            // Draft was already stashed at handleStart (no
            // workspace_id since create itself failed); just bounce.
            bounceToLogin();
            return;
          }
          toastError(t("docdrop.create_error"), { description: e.message });
        },
      },
    );
  }

  function handleStart() {
    if (label.trim().length === 0 || files.length === 0) return;

    // Option E: stash the draft IMMEDIATELY so an unexpected 401 in
    // either create OR upload doesn't lose the advisor's input. We
    // re-stash with workspace_id once create succeeds (Option D) so
    // a 401 mid-upload preserves the workspace pointer too.
    saveUploadDraft({
      label: label.trim(),
      data_origin: dataOrigin,
      files,
      ...(pendingWorkspaceId !== null ? { workspace_id: pendingWorkspaceId } : {}),
    });

    // Option D: if we have a workspace_id from a prior interrupted
    // upload, skip create and upload directly. SHA256 dedup in the
    // upload endpoint makes this safe even if some files succeeded
    // before the prior 401. On 404 (workspace deleted server-side),
    // executeUpload falls back to fresh create.
    if (pendingWorkspaceId !== null) {
      executeUpload(pendingWorkspaceId, true);
      return;
    }
    executeCreateThenUpload();
  }

  const isSubmitting = createWorkspace.isPending || upload.isPending;
  const canSubmit = label.trim().length > 0 && files.length > 0 && !isSubmitting;

  return (
    <section
      aria-labelledby="docdrop-title"
      className="flex flex-col gap-4 border border-hairline-2 bg-paper p-6 shadow-sm"
    >
      <header>
        <h2 id="docdrop-title" className="font-serif text-xl font-medium tracking-tight text-ink">
          {t("docdrop.title")}
        </h2>
        <p className="mt-1 text-[12px] leading-relaxed text-muted">{t("docdrop.intro")}</p>
      </header>

      <div className="grid grid-cols-[1fr_220px] gap-3">
        <label className="flex flex-col gap-1">
          <span className="font-mono text-[10px] uppercase tracking-widest text-muted">
            {t("docdrop.label_label")}
          </span>
          <input
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder={t("docdrop.label_placeholder")}
            disabled={isSubmitting}
            className="border border-hairline-2 bg-paper px-3 py-2 font-sans text-[13px] text-ink focus:border-accent focus:outline-none"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="font-mono text-[10px] uppercase tracking-widest text-muted">
            {t("docdrop.origin_label")}
          </span>
          <select
            value={dataOrigin}
            onChange={(e) => setDataOrigin(e.target.value as "real_derived" | "synthetic")}
            disabled={isSubmitting}
            className="border border-hairline-2 bg-paper px-3 py-2 font-sans text-[13px] text-ink focus:border-accent focus:outline-none"
          >
            <option value="synthetic">{t("docdrop.origin_synthetic")}</option>
            <option value="real_derived">{t("docdrop.origin_real")}</option>
          </select>
        </label>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={cn(
          // Base dropzone surface — beefier than the prior subtle hint:
          // 4px dashed border so the affordance is visible at a glance.
          "flex flex-col items-center justify-center gap-2 border-4 border-dashed p-8",
          "motion-safe:transition-[background-color,border-color,transform] motion-safe:duration-150",
          isDragOver
            ? // Active state: accent border, deeper shaded background,
              // and (with motion-safe) a subtle scale lift on the icon
              // — see Upload icon className below.
              "border-accent bg-accent/10 ring-1 ring-accent/40"
            : "border-hairline-2 bg-paper-2",
        )}
      >
        {/* Status-only aria-live region: only announces the
            transition into "release to drop" hint, not the entire
            dropzone subtree. Without this scoping, screen readers
            re-narrate the icon + 3 paragraphs on every drag toggle. */}
        <span className="sr-only" aria-live="polite">
          {isDragOver ? t("polish_b.docdrop.dropzone_active_hint") : ""}
        </span>
        <Upload
          aria-hidden
          className={cn(
            "h-6 w-6",
            "motion-safe:transition-transform motion-safe:duration-150",
            isDragOver ? "scale-125 text-accent" : "text-muted",
          )}
        />
        <p
          className={cn(
            "font-sans text-[13px]",
            isDragOver ? "font-medium text-accent-2" : "text-ink",
          )}
        >
          {isDragOver ? t("polish_b.docdrop.dropzone_active_hint") : t("docdrop.dropzone_primary")}
        </p>
        <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
          {t("docdrop.dropzone_secondary")}
        </p>
        <p className="font-mono text-[9px] uppercase tracking-widest text-muted">
          {t("polish_b.docdrop.size_limit_hint", {
            limit_mb: Math.round(MAX_FILE_BYTES / (1024 * 1024)),
          })}
        </p>
        <input
          id="docdrop-file-input"
          type="file"
          multiple
          onChange={handleFilesPicked}
          disabled={isSubmitting}
          className="sr-only"
          aria-label={t("docdrop.pick_files")}
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => document.getElementById("docdrop-file-input")?.click()}
          disabled={isSubmitting}
        >
          {t("docdrop.pick_files")}
        </Button>
      </div>

      {pendingFileMeta.length > 0 && files.length === 0 && (
        <section
          aria-labelledby="docdrop-recovered-title"
          className="flex flex-col gap-2 border border-accent/40 bg-paper-2 p-3"
        >
          <div className="flex items-baseline justify-between">
            <h3
              id="docdrop-recovered-title"
              className="font-mono text-[10px] uppercase tracking-widest text-accent"
            >
              {t("docdrop.draft_recovered_title")}
            </h3>
            <Button type="button" variant="ghost" size="sm" onClick={discardDraft}>
              {t("docdrop.draft_discard")}
            </Button>
          </div>
          <p className="font-sans text-[12px] text-muted">
            {t("docdrop.draft_recovered_body", { count: pendingFileMeta.length })}
          </p>
          <ul className="flex flex-col divide-y divide-hairline border border-hairline-2 bg-paper">
            {pendingFileMeta.map((meta, index) => (
              <li
                key={`pending-${meta.name}-${index}`}
                className="flex items-center justify-between px-3 py-2"
              >
                <span className="font-sans text-[12px] text-ink">{meta.name}</span>
                <span className="font-mono text-[10px] text-muted">{formatBytes(meta.size)}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {retryableFiles.length > 0 && retryWorkspaceId !== null && (
        <section
          aria-labelledby="docdrop-retry-title"
          className="flex flex-col gap-2 border border-danger/40 bg-paper-2 p-3"
        >
          <div className="flex items-baseline justify-between">
            <h3
              id="docdrop-retry-title"
              className="font-mono text-[10px] uppercase tracking-widest text-danger"
            >
              {t("docdrop.retry_failed_title")}
            </h3>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={retryFailedFiles}
              disabled={isSubmitting}
            >
              {isSubmitting
                ? t("docdrop.retry_failed_pending")
                : t("docdrop.retry_failed_action", { count: retryableFiles.length })}
            </Button>
          </div>
          <p className="font-sans text-[12px] text-muted">
            {t("docdrop.retry_failed_body", { count: retryableFiles.length })}
          </p>
          <ul className="flex flex-col divide-y divide-hairline border border-hairline-2 bg-paper">
            {retryableFiles.map((file, index) => (
              <li
                key={`retry-${file.name}-${index}`}
                className="flex items-center justify-between px-3 py-2"
              >
                <span className="font-sans text-[12px] text-ink">{file.name}</span>
                <span className="font-mono text-[10px] text-muted">{formatBytes(file.size)}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {files.length > 0 && (
        <ul className="flex flex-col divide-y divide-hairline border border-hairline">
          {files.map((file, index) => (
            <li
              key={`${file.name}-${index}`}
              className="flex items-center justify-between px-3 py-2"
            >
              <span className="flex flex-col">
                <span className="font-sans text-[12px] text-ink">{file.name}</span>
                <span className="font-mono text-[10px] text-muted">{formatBytes(file.size)}</span>
              </span>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => removeFile(index)}
                aria-label={t("docdrop.remove_file", { name: file.name })}
              >
                <X aria-hidden className="h-3.5 w-3.5" />
              </Button>
            </li>
          ))}
        </ul>
      )}

      <footer className="flex items-center justify-between border-t border-hairline pt-4">
        <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
          {t("docdrop.file_count", { count: files.length })}
        </p>
        <Button type="button" size="sm" onClick={handleStart} disabled={!canSubmit}>
          {isSubmitting ? t("docdrop.starting") : t("docdrop.start")}
        </Button>
      </footer>
    </section>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
