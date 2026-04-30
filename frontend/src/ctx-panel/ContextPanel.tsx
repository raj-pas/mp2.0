import * as Tabs from "@radix-ui/react-tabs";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/button";
import { useLocalStorage } from "../lib/local-storage";
import { cn } from "../lib/cn";

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

export function ContextPanel({ kind, breadcrumb }: ContextPanelProps) {
  const { t } = useTranslation();
  const [collapsed, setCollapsed] = useLocalStorage<boolean>("mp20_ctx_panel_collapsed", false);
  const tabs = TAB_DEFS[kind];
  const firstTab = tabs[0];

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
      <Tabs.Root defaultValue={firstTab?.value} className="flex flex-1 flex-col overflow-hidden">
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
        {tabs.map((tab) => (
          <Tabs.Content key={tab.value} value={tab.value} className="flex-1 overflow-y-auto p-3.5">
            <CtxPlaceholder kind={kind} tab={tab.value} />
          </Tabs.Content>
        ))}
      </Tabs.Root>
    </aside>
  );
}

function CtxPlaceholder({ kind, tab }: { kind: ContextPanelKind; tab: string }) {
  const { t } = useTranslation();
  return (
    <div className="flex h-full flex-col items-center justify-center text-center">
      <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
        {t(`ctx.kinds.${kind}`)} · {t(`ctx.tabs.${tab}`)}
      </p>
      <p className="mt-2 max-w-[260px] text-[12px] leading-relaxed text-muted">
        {t("ctx.placeholder_body")}
      </p>
    </div>
  );
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
