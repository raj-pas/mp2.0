import { toast } from "sonner";

/**
 * Thin wrapper around Sonner for canon-aligned UX (locked decision #21):
 *   - non-destructive saves -> toast.success
 *   - preview/network errors -> toast.error with retry action
 *   - hard-destructive operations use ConfirmDialog instead, not toasts
 *
 * Phase 5b UX-polish pass — adds dedup so a rapid mutation chain
 * (e.g., bulk-resolve onSuccess → toast → invalidate → re-render →
 * onSuccess re-fire under React-strict-mode-double-invoke) doesn't
 * stack the same toast twice. Identical (kind, message, description)
 * triples within DEDUP_WINDOW_MS get suppressed.
 */

const DEDUP_WINDOW_MS = 1500;
const recentToasts = new Map<string, number>();

function shouldFire(key: string): boolean {
  const now = Date.now();
  const lastFired = recentToasts.get(key);
  if (lastFired !== undefined && now - lastFired < DEDUP_WINDOW_MS) {
    return false;
  }
  recentToasts.set(key, now);
  // Periodic cleanup so the Map doesn't grow without bound.
  if (recentToasts.size > 32) {
    for (const [k, t] of recentToasts.entries()) {
      if (now - t > DEDUP_WINDOW_MS * 2) recentToasts.delete(k);
    }
  }
  return true;
}

export function toastSuccess(message: string, description?: string) {
  if (!shouldFire(`success::${message}::${description ?? ""}`)) return;
  toast.success(message, description ? { description } : undefined);
}

export function toastError(
  message: string,
  options?: { description?: string; onRetry?: () => void; retryLabel?: string },
) {
  if (!shouldFire(`error::${message}::${options?.description ?? ""}`)) return;
  toast.error(message, {
    description: options?.description,
    action: options?.onRetry
      ? {
          label: options.retryLabel ?? "Retry",
          onClick: options.onRetry,
        }
      : undefined,
  });
}

export function toastInfo(message: string, description?: string) {
  if (!shouldFire(`info::${message}::${description ?? ""}`)) return;
  toast(message, description ? { description } : undefined);
}
