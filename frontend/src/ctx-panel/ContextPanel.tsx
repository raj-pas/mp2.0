import * as Tabs from "@radix-ui/react-tabs";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/button";
import { useLocalStorage } from "../lib/local-storage";
import { cn } from "../lib/cn";

import { AccountContext } from "./AccountContext";
import { GoalContext } from "./GoalContext";
import { HouseholdContext } from "./HouseholdContext";

export type ContextPanelKind = "household" | "account" | "goal";

interface ContextPanelProps {
  kind: ContextPanelKind;
  breadcrumb: string[];
}

const TAB_DEFS: Record<ContextPanelKind, { value: string; labelKey: string }[]> = {
  household: [
    { value: "overview", labelKey: "ctx.tabs.overview" },
    { value: "allocation", labelKey: "ctx.tabs.allocation" },
    { value: "projections", labelKey: "ctx.tabs.projections" },
    { value: "history", labelKey: "ctx.tabs.history" },
  ],
  account: [
    { value: "overview", labelKey: "ctx.tabs.overview" },
    { value: "allocation", labelKey: "ctx.tabs.allocation" },
    { value: "goals", labelKey: "ctx.tabs.goals" },
  ],
  goal: [
    { value: "overview", labelKey: "ctx.tabs.overview" },
    { value: "allocation", labelKey: "ctx.tabs.allocation" },
    { value: "projections", labelKey: "ctx.tabs.projections" },
  ],
};

/**
 * Per-kind localStorage keys for active-tab persistence (P3.2 §A1.32).
 * Each kind gets its own key so switching between household/account/goal
 * preserves the last-active tab independently for each.
 */
const TAB_STORAGE_KEYS: Record<ContextPanelKind, string> = {
  household: "mp20_ctx_tab_household",
  account: "mp20_ctx_tab_account",
  goal: "mp20_ctx_tab_goal",
};

export function ContextPanel({ kind, breadcrumb }: ContextPanelProps) {
  const { t } = useTranslation();
  const [collapsed, setCollapsed] = useLocalStorage<boolean>("mp20_ctx_panel_collapsed", false);
  const tabs = TAB_DEFS[kind];
  const firstTab = tabs[0];
  const defaultTabValue = firstTab?.value ?? "overview";

  // Controlled Tabs.Root state with per-kind localStorage persistence
  // (P3.2 plan v20 §A1.32). useLocalStorage shares state cross-component
  // and survives reloads; if the persisted tab no longer exists for this
  // kind (e.g. catalog change), fall back to the first tab defensively.
  const [persistedTab, setPersistedTab] = useLocalStorage<string>(
    TAB_STORAGE_KEYS[kind],
    defaultTabValue,
  );
  const isKnownTab = tabs.some((t) => t.value === persistedTab);
  const activeTab = isKnownTab ? persistedTab : defaultTabValue;

  if (collapsed) {
    return (
      <aside
        className="flex w-10 flex-shrink-0 flex-col items-center border border-hairline bg-paper py-2 shadow-sm"
        aria-label={t("ctx.panel_label")}
      >
        <Button
          variant="ghost"
          size="icon"
          aria-label={t("ctx.expand")}
          onClick={() => setCollapsed(false)}
        >
          <ChevronLeft aria-hidden className="h-4 w-4" />
        </Button>
      </aside>
    );
  }

  return (
    <aside
      className="flex w-[360px] flex-shrink-0 flex-col overflow-hidden border border-hairline bg-paper shadow-sm"
      aria-label={t("ctx.panel_label")}
    >
      <div className="flex flex-shrink-0 items-center justify-between border-b border-hairline bg-paper px-3.5 py-2.5">
        <Breadcrumb segments={breadcrumb} />
        <Button
          variant="outline"
          size="icon"
          aria-label={t("ctx.collapse")}
          onClick={() => setCollapsed(true)}
        >
          <ChevronRight aria-hidden className="h-4 w-4" />
        </Button>
      </div>
      <Tabs.Root
        value={activeTab}
        onValueChange={setPersistedTab}
        className="flex flex-1 flex-col overflow-hidden"
      >
        <Tabs.List className="flex flex-shrink-0 overflow-x-auto border-b border-hairline bg-paper">
          {tabs.map((tab) => (
            <Tabs.Trigger
              key={tab.value}
              value={tab.value}
              className={cn(
                "border-b-2 border-transparent px-3 py-2.5 font-sans text-[11px] font-medium text-muted transition-colors",
                "hover:text-ink",
                "data-[state=active]:border-accent data-[state=active]:text-ink",
              )}
            >
              {t(tab.labelKey)}
            </Tabs.Trigger>
          ))}
        </Tabs.List>
        <ContextBody kind={kind} tab={activeTab} />
      </Tabs.Root>
    </aside>
  );
}

function ContextBody({ kind, tab }: { kind: ContextPanelKind; tab: string }) {
  if (kind === "household") return <HouseholdContext tab={tab} />;
  if (kind === "account") return <AccountContext tab={tab} />;
  return <GoalContext tab={tab} />;
}

function Breadcrumb({ segments }: { segments: string[] }) {
  const { t } = useTranslation();
  return (
    <nav
      aria-label={t("ctx.breadcrumb_label")}
      className="flex items-center gap-1 overflow-hidden font-mono text-[11px] tracking-wide text-muted"
    >
      {segments.map((seg, idx) => {
        const isLast = idx === segments.length - 1;
        return (
          <span
            key={`${seg}-${idx}`}
            className={cn(
              "truncate",
              isLast && "font-serif text-[14px] italic text-ink tracking-tight",
            )}
          >
            {idx > 0 && <ChevronRight aria-hidden className="mr-1 inline h-3 w-3 text-muted-2" />}
            {seg}
          </span>
        );
      })}
    </nav>
  );
}
