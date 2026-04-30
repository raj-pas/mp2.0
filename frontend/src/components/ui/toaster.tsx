import { Toaster as SonnerToaster } from "sonner";

export function Toaster() {
  return (
    <SonnerToaster
      position="bottom-right"
      toastOptions={{
        classNames: {
          toast: "border border-hairline-2 bg-paper text-ink shadow-sm font-sans text-[12px]",
          description: "text-muted",
          actionButton: "bg-ink text-paper font-mono text-[10px] uppercase tracking-widest",
          cancelButton: "bg-paper-2 text-muted font-mono text-[10px] uppercase",
        },
      }}
    />
  );
}
