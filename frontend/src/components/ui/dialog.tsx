import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import * as React from "react";
import { useTranslation } from "react-i18next";

import { cn } from "../../lib/cn";

/**
 * shadcn-pattern Radix Dialog wrapper.
 *
 * Used for modal overlays (RealignModal R6, ConfirmDialog future).
 * For full-screen takeovers like CompareScreen we use the same primitive
 * but pass a custom Content className.
 */
const Dialog = DialogPrimitive.Root;
const DialogTrigger = DialogPrimitive.Trigger;
const DialogPortal = DialogPrimitive.Portal;
const DialogClose = DialogPrimitive.Close;
const DialogTitle = DialogPrimitive.Title;
const DialogDescription = DialogPrimitive.Description;

const DialogOverlay = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Overlay
    ref={ref}
    className={cn(
      "fixed inset-0 z-40 bg-ink/55 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
      className,
    )}
    {...props}
  />
));
DialogOverlay.displayName = DialogPrimitive.Overlay.displayName;

interface DialogContentProps extends React.ComponentPropsWithoutRef<
  typeof DialogPrimitive.Content
> {
  /** When true, omits the default centered max-width frame so callers can
   * render full-screen takeovers (CompareScreen). */
  fullScreen?: boolean;
}

const DialogContent = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  DialogContentProps
>(({ className, children, fullScreen = false, ...props }, ref) => {
  const { t } = useTranslation();
  return (
    <DialogPortal>
      <DialogOverlay />
      <DialogPrimitive.Content
        ref={ref}
        className={cn(
          "fixed z-50 border border-hairline-2 bg-paper shadow-lg focus:outline-none",
          fullScreen
            ? "inset-4 overflow-y-auto"
            : "left-1/2 top-1/2 max-h-[85vh] w-[min(92vw,640px)] -translate-x-1/2 -translate-y-1/2 overflow-y-auto",
          className,
        )}
        {...props}
      >
        {children}
        <DialogPrimitive.Close
          className="absolute right-3 top-3 grid h-7 w-7 place-items-center text-muted hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          aria-label={t("common.close")}
        >
          <X aria-hidden className="h-4 w-4" />
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPortal>
  );
});
DialogContent.displayName = DialogPrimitive.Content.displayName;

export {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogOverlay,
  DialogPortal,
  DialogTitle,
  DialogTrigger,
};
