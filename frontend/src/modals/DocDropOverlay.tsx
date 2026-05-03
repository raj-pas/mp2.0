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

interface DocDropOverlayProps {
  /** Called with the new workspace external_id once create + upload succeed. */
  onWorkspaceReady: (workspaceId: string) => void;
}

export function DocDropOverlay({ onWorkspaceReady }: DocDropOverlayProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [label, setLabel] = useState("");
  const [dataOrigin, setDataOrigin] = useState<"real_derived" | "synthetic">("synthetic");
  const [files, setFiles] = useState<File[]>([]);
  const [pendingFileMeta, setPendingFileMeta] = useState<UploadFileMeta[]>([]);
  const [isDragOver, setDragOver] = useState(false);

  const createWorkspace = useCreateWorkspace();
  const upload = useUploadDocuments();

  // Phase 5b.8: restore an upload draft if a prior attempt was
  // interrupted by a 401. We can preserve label + data_origin +
  // file metadata, but not the File bytes (browsers don't expose
  // them across sessionStorage). The pendingFileMeta state shows
  // the advisor which files they originally dropped so they can
  // re-pick the same set.
  useEffect(() => {
    const draft = consumeUploadDraft();
    if (draft === null) return;
    setLabel(draft.label);
    setDataOrigin(draft.data_origin);
    setPendingFileMeta(draft.files);
    toastSuccess(
      t("docdrop.draft_restored_title"),
      t("docdrop.draft_restored_body", {
        count: draft.files.length,
        label: draft.label,
      }),
    );
  }, [t]);

  function handleFilesPicked(event: ChangeEvent<HTMLInputElement>) {
    // FileList from `event.target.files` is a LIVE reference: clearing
    // `event.target.value` empties it, which races against React's
    // deferred setFiles callback. Snapshot to a plain array BEFORE
    // clearing the input so the callback sees stable data.
    const picked = event.target.files;
    if (picked === null || picked.length === 0) return;
    const snapshot = Array.from(picked);
    event.target.value = "";
    setFiles((prev) => [...prev, ...snapshot]);
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
    setFiles((prev) => [...prev, ...snapshot]);
    if (pendingFileMeta.length > 0) setPendingFileMeta([]);
  }

  function removeFile(index: number) {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }

  function discardDraft() {
    setLabel("");
    setDataOrigin("synthetic");
    setPendingFileMeta([]);
    clearUploadDraft();
  }

  function handleStart() {
    if (label.trim().length === 0 || files.length === 0) return;
    createWorkspace.mutate(
      { label: label.trim(), data_origin: dataOrigin },
      {
        onSuccess: (workspace) => {
          upload.mutate(
            { workspaceId: workspace.external_id, files },
            {
              onSuccess: (response) => {
                // The upload endpoint partial-failure tolerates per-file
                // errors. Surface that explicitly to the advisor so
                // they don't think every file went through when half
                // were rejected.
                const failedFiles = response.ignored
                  .filter((row) => row.reason === "upload_failed")
                  .map((row) => row.filename);
                if (response.uploaded.length === 0) {
                  toastError(t("docdrop.upload_error"), {
                    description: t("docdrop.upload_all_failed", {
                      count: failedFiles.length,
                    }),
                  });
                } else if (failedFiles.length > 0) {
                  toastSuccess(
                    t("docdrop.upload_partial_title"),
                    t("docdrop.upload_partial_body", {
                      uploaded: response.uploaded.length,
                      failed: failedFiles.length,
                      names: failedFiles.join(", "),
                    }),
                  );
                  onWorkspaceReady(workspace.external_id);
                  setLabel("");
                  setFiles([]);
                } else {
                  toastSuccess(
                    t("docdrop.upload_success_title"),
                    t("docdrop.upload_success_body"),
                  );
                  onWorkspaceReady(workspace.external_id);
                  setLabel("");
                  setFiles([]);
                }
              },
              onError: (err) => {
                const e = normalizeApiError(err, t("docdrop.upload_error"));
                if (isAuthError(e)) {
                  // Session expired mid-upload. Save metadata so the
                  // advisor doesn't have to retype the workspace label
                  // or guess which files were attempted; invalidating
                  // the session query bounces SessionGate to LoginRoute.
                  saveUploadDraft({
                    label: label.trim(),
                    data_origin: dataOrigin,
                    files,
                  });
                  toastError(t("docdrop.session_expired_title"), {
                    description: t("docdrop.session_expired_body"),
                  });
                  queryClient.invalidateQueries({ queryKey: SESSION_QUERY_KEY });
                  return;
                }
                toastError(t("docdrop.upload_error"), { description: e.message });
              },
            },
          );
        },
        onError: (err) => {
          const e = normalizeApiError(err, t("docdrop.create_error"));
          if (isAuthError(e)) {
            saveUploadDraft({
              label: label.trim(),
              data_origin: dataOrigin,
              files,
            });
            toastError(t("docdrop.session_expired_title"), {
              description: t("docdrop.session_expired_body"),
            });
            queryClient.invalidateQueries({ queryKey: SESSION_QUERY_KEY });
            return;
          }
          toastError(t("docdrop.create_error"), { description: e.message });
        },
      },
    );
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
          "flex flex-col items-center justify-center gap-2 border-2 border-dashed bg-paper-2 p-8 transition-colors",
          isDragOver ? "border-accent bg-paper" : "border-hairline-2",
        )}
      >
        <Upload aria-hidden className="h-6 w-6 text-muted" />
        <p className="font-sans text-[13px] text-ink">{t("docdrop.dropzone_primary")}</p>
        <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
          {t("docdrop.dropzone_secondary")}
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
