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
import { type ChangeEvent, type DragEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/button";
import { useCreateWorkspace, useUploadDocuments } from "../lib/review";
import { normalizeApiError } from "../lib/api-error";
import { toastError, toastSuccess } from "../lib/toast";
import { cn } from "../lib/cn";

interface DocDropOverlayProps {
  /** Called with the new workspace external_id once create + upload succeed. */
  onWorkspaceReady: (workspaceId: string) => void;
}

export function DocDropOverlay({ onWorkspaceReady }: DocDropOverlayProps) {
  const { t } = useTranslation();
  const [label, setLabel] = useState("");
  const [dataOrigin, setDataOrigin] = useState<"real_derived" | "synthetic">("synthetic");
  const [files, setFiles] = useState<File[]>([]);
  const [isDragOver, setDragOver] = useState(false);

  const createWorkspace = useCreateWorkspace();
  const upload = useUploadDocuments();

  function handleFilesPicked(event: ChangeEvent<HTMLInputElement>) {
    const picked = event.target.files;
    if (picked === null) return;
    setFiles((prev) => [...prev, ...Array.from(picked)]);
    event.target.value = "";
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragOver(false);
    const dropped = event.dataTransfer.files;
    if (dropped.length === 0) return;
    setFiles((prev) => [...prev, ...Array.from(dropped)]);
  }

  function removeFile(index: number) {
    setFiles((prev) => prev.filter((_, i) => i !== index));
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
              onSuccess: () => {
                toastSuccess(t("docdrop.upload_success_title"), t("docdrop.upload_success_body"));
                onWorkspaceReady(workspace.external_id);
                setLabel("");
                setFiles([]);
              },
              onError: (err) => {
                const e = normalizeApiError(err, t("docdrop.upload_error"));
                toastError(t("docdrop.upload_error"), { description: e.message });
              },
            },
          );
        },
        onError: (err) => {
          const e = normalizeApiError(err, t("docdrop.create_error"));
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
