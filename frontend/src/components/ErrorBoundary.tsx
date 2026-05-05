import type { ErrorInfo, ReactNode } from "react";
import { Component } from "react";

import i18n from "../i18n";
import { cn } from "../lib/cn";
import { toastError } from "../lib/toast";

/**
 * Top-level + per-route React ErrorBoundary (locked decision #31a).
 *
 * Catches render errors before they crash the whole app. Per-route
 * boundary scoping means a broken Goal view leaves Household + Account
 * routes still working. Fallback UI uses paper/ink aesthetic with retry
 * + "report this" copy per locked decision #21.
 *
 * No third-party error reporting service in v1 (locked decision #31c).
 * Phase B can layer Sentry/GlitchTip on top of this boundary.
 *
 * Strings routed through i18n.t (singleton, not hook) so the class
 * component honors locked decision #28a.
 */
type Props = {
  children: ReactNode;
  /** Label rendered in the fallback (e.g. "Goal view"). */
  scope?: string;
};

type State = {
  hasError: boolean;
  error: Error | null;
};

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  override componentDidCatch(error: Error, info: ErrorInfo): void {
    // OpenTelemetry instrumentation (locked decision #31b) captures
    // unhandled errors via console; production OTLP picks them up via
    // browser instrumentation.
    console.error("[ErrorBoundary]", this.props.scope ?? "root", error, info);
  }

  reset = (): void => {
    this.setState({ hasError: false, error: null });
  };

  override render(): ReactNode {
    if (!this.state.hasError) {
      return this.props.children;
    }

    const description = this.props.scope
      ? i18n.t("errors.boundary_scoped", { scope: this.props.scope })
      : i18n.t("errors.boundary_unscoped");

    return (
      <div
        role="alert"
        className={cn("mx-auto my-12 max-w-xl border border-hairline-2 bg-paper p-8 shadow")}
      >
        <h1 className="font-serif text-2xl font-semibold text-ink">
          {i18n.t("errors.boundary_title")}
        </h1>
        <p className="mt-3 text-sm text-muted">{description}</p>
        {this.state.error?.message ? (
          <pre className="mt-4 overflow-auto bg-paper-2 p-3 font-mono text-xs text-ink-2">
            {this.state.error.message}
          </pre>
        ) : null}
        <div className="mt-6 flex gap-3">
          <button
            type="button"
            onClick={this.reset}
            className={cn(
              "border border-ink bg-ink px-4 py-2 text-xs font-medium uppercase tracking-wider text-paper",
              "hover:bg-accent-2 transition-colors",
              "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent",
            )}
          >
            {i18n.t("errors.retry")}
          </button>
          <button
            type="button"
            onClick={() => {
              // Local-capture report (P3.1 polish). Future "report this"
              // channel wires up via the Feedback button in the chrome.
              toastError(i18n.t("errors.report_phase_b"));
            }}
            className={cn(
              "border border-hairline-2 bg-paper-2 px-4 py-2 text-xs font-medium uppercase tracking-wider text-ink-2",
              "hover:bg-paper transition-colors",
              "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent",
            )}
          >
            {i18n.t("errors.report_this")}
          </button>
        </div>
      </div>
    );
  }
}
