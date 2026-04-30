/**
 * Holding shell for the v36 UI/UX rewrite (Phase R0).
 *
 * Structure pending across R2–R9 phases:
 *   R2 — TopBar + Stage + ContextPanel chrome (BrowserRouter)
 *   R3 — HouseholdRoute + AccountRoute + GoalRoute + Treemap
 *   R4 — Goal allocation + projections + optimizer output + moves
 *   R5 — HouseholdWizard (5-step fallback)
 *   R6 — Realignment + Compare + History
 *   R7 — Doc-drop + Conflict resolution (replaces ReviewShell)
 *   R8 — Methodology overlay
 *   R9 — CMA Workbench rebuild (analyst-only)
 *   R10 — Real-PII testing + parity sweep + final polish
 *
 * Per locked decision #20 (no feature flag), the old App.tsx /
 * ReviewShell / CmaWorkbench surfaces are deleted in this phase rather
 * than coexisting; future phases progressively populate this shell.
 *
 * TODO(canon §13.0.1): pilot-mode disclaimer surface deferred to
 * iterative scope per locked decision #17. Add ribbon under topbar or
 * per-recommendation footer when finalized.
 */
import { useTranslation } from "react-i18next";

import { ErrorBoundary } from "./components/ErrorBoundary";
import { cn } from "./lib/cn";

function App() {
  const { t } = useTranslation();

  return (
    <ErrorBoundary>
      <div className="flex min-h-screen flex-col bg-paper text-ink">
        <header
          className={cn(
            "flex h-12 flex-shrink-0 items-center gap-4 border-b border-hairline-2 bg-paper px-5 shadow-sm",
          )}
        >
          <div className="flex items-center gap-2">
            <div className="grid h-6 w-6 place-items-center bg-ink font-serif text-sm italic font-semibold text-paper">
              M
            </div>
            <div>
              <span className="font-serif text-sm font-medium tracking-tight text-ink">
                {t("topbar.brand")}
              </span>
              <span className="ml-2 font-mono text-[9px] uppercase tracking-widest text-muted">
                {t("topbar.brand_subtitle")}
              </span>
            </div>
          </div>
          <div className="flex-1" />
        </header>

        <main className="flex flex-1 flex-col items-center justify-center p-12">
          <div className="max-w-2xl text-center">
            <p className="mb-3 font-mono text-[10px] uppercase tracking-widest text-muted">
              {t("scaffold.phase_label")}
            </p>
            <h1 className="font-serif text-4xl font-medium tracking-tight text-ink">
              {t("scaffold.title")}
            </h1>
            <p className="mt-4 text-sm leading-relaxed text-muted">{t("scaffold.description")}</p>
          </div>
        </main>
      </div>
    </ErrorBoundary>
  );
}

export default App;
