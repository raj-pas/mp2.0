import { useTranslation } from "react-i18next";

import { Skeleton } from "../components/ui/skeleton";
import { useOptimizerOutput } from "../lib/preview";
import { formatCadCompact, formatPct } from "../lib/format";

interface OptimizerOutputWidgetProps {
  householdId: string;
  goalId: string;
}

export function OptimizerOutputWidget({ householdId, goalId }: OptimizerOutputWidgetProps) {
  const { t } = useTranslation();
  const query = useOptimizerOutput(householdId, goalId);

  if (query.isPending) {
    return (
      <Section title={t("optimizer_output.section_title")}>
        <Skeleton className="h-12 w-full" />
      </Section>
    );
  }
  if (query.isError || query.data === undefined) {
    return (
      <Section title={t("optimizer_output.section_title")}>
        <p role="alert" className="font-mono text-[10px] uppercase tracking-widest text-danger">
          {t("errors.preview_failed")}
        </p>
      </Section>
    );
  }

  const data = query.data;
  const pUsedPct = (data.p_used * 100).toFixed(0);
  return (
    <Section title={t("optimizer_output.section_title")}>
      <div className="grid grid-cols-2 gap-4">
        <Stat
          label={t("optimizer_output.improvement_pct", { p: pUsedPct })}
          primary={formatPct(data.improvement_pct, 1)}
          tone="accent"
        />
        <Stat
          label={t("optimizer_output.effective_score")}
          primary={data.effective_descriptor}
          secondary={`${data.effective_score_1_5} / 5 · ${t(`routes.goal.tier_${data.tier}`)}`}
        />
        <Stat
          label={t("optimizer_output.ideal_label", { p: pUsedPct })}
          primary={formatCadCompact(data.ideal_low)}
        />
        <Stat
          label={t("optimizer_output.current_label", { p: pUsedPct })}
          primary={formatCadCompact(data.current_low)}
        />
      </div>
    </Section>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border border-hairline-2 bg-paper p-4 shadow-sm">
      <h3 className="mb-3 font-mono text-[10px] uppercase tracking-widest text-muted">{title}</h3>
      {children}
    </section>
  );
}

function Stat({
  label,
  primary,
  secondary,
  tone = "default",
}: {
  label: string;
  primary: string;
  secondary?: string;
  tone?: "default" | "accent";
}) {
  const primaryClass =
    tone === "accent"
      ? "font-serif text-2xl font-medium text-accent-2"
      : "font-serif text-lg font-medium text-ink";
  return (
    <div className="flex flex-col">
      <span className="font-mono text-[9px] uppercase tracking-widest text-muted">{label}</span>
      <span className={primaryClass}>{primary}</span>
      {secondary !== undefined && (
        <span className="font-mono text-[10px] text-muted">{secondary}</span>
      )}
    </div>
  );
}
