import { toast } from "sonner";

/**
 * Thin wrapper around Sonner for canon-aligned UX (locked decision #21):
 *   - non-destructive saves -> toast.success
 *   - preview/network errors -> toast.error with retry action
 *   - hard-destructive operations use ConfirmDialog instead, not toasts
 */

export function toastSuccess(message: string, description?: string) {
  toast.success(message, description ? { description } : undefined);
}

export function toastError(
  message: string,
  options?: { description?: string; onRetry?: () => void; retryLabel?: string },
) {
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
  toast(message, description ? { description } : undefined);
}
