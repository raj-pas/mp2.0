import * as Tabs from "@radix-ui/react-tabs";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import { useRememberedClientId } from "../chrome/ClientPicker";
import { RiskBandTrack } from "../charts/RiskBandTrack";
import { Skeleton } from "../components/ui/skeleton";
import { findGoal, useHousehold } from "../lib/household";
import { formatCad } from "../lib/format";
import { useOverrideHistory } from "../lib/preview";
import { descriptorFor, isCanonRisk } from "../lib/risk";

export function GoalContext() {
  const { t } = useTranslation();
  const { goalId } = useParams<{ goalId: string }>();
  const [rememberedId] = useRememberedClientId();
  const householdQuery = useHousehold(rememberedId);

  if (householdQuery.isPending) {
    return <Skeleton className="h-32 w-full" />;
  }
  const goal =
    goalId !== undefined && householdQuery.data ? findGoal(householdQuery.data, goalId) : null;
  if (goal === null) {
    return (
      <p className="font-mono text-[10px] uppercase tracking-widest text-danger">
        {t("routes.goal.missing_goal")}
      </p>
    );
  }

  const descriptor = descriptorFor(goal.goal_risk_score, t);
  const goalScore = isCanonRisk(goal.goal_risk_score) ? goal.goal_risk_score : null;

  return (
    <>
      <Tabs.Content value="overview" className="flex-1 overflow-y-auto p-3.5">
        <CtxSection label={t("ctx.section.goal")}>
          <p className="font-serif text-base text-ink">{goal.name}</p>
        </CtxSection>
        <CtxSection label={t("routes.goal.kpi_target")}>
          <p className="font-serif text-lg font-medium text-ink">
            {goal.target_amount !== null ? formatCad(goal.target_amount) : "—"}
          </p>
        </CtxSection>
        <CtxSection label={t("routes.goal.kpi_funded")}>
          <p className="font-serif text-lg font-medium text-ink">
            {formatCad(goal.current_funded_amount)}
          </p>
        </CtxSection>
        <CtxSection label={t("routes.goal.kpi_risk")}>
          <p className="mb-2 font-mono text-[11px] uppercase tracking-widest text-ink">
            {descriptor ?? t("routes.goal.kpi_risk_unset")}
          </p>
          <RiskBandTrack score={goalScore} size="sm" />
        </CtxSection>
      </Tabs.Content>

      <Tabs.Content value="allocation" className="flex-1 overflow-y-auto p-3.5">
        <CtxSection label={t("routes.goal.linked_accounts_title")}>
          {goal.account_allocations.length === 0 ? (
            <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
              {t("empty.no_holdings")}
            </p>
          ) : (
            <ul className="flex flex-col divide-y divide-hairline">
              {goal.account_allocations
                .filter((l) => Number(l.allocated_amount) > 0)
                .map((link) => (
                  <li
                    key={link.id}
                    className="flex items-baseline justify-between py-1.5 font-mono text-[10px]"
                  >
                    <span className="text-ink">{link.account_id}</span>
                    <span className="text-accent-2">
                      {formatCad(Number(link.allocated_amount))}
                    </span>
                  </li>
                ))}
            </ul>
          )}
        </CtxSection>
      </Tabs.Content>

      <Tabs.Content value="projections" className="flex-1 overflow-y-auto p-3.5">
        <CtxSection label={t("risk_slider.history_title")}>
          <OverrideHistoryList goalId={goalId ?? null} />
        </CtxSection>
      </Tabs.Content>
    </>
  );
}

function OverrideHistoryList({ goalId }: { goalId: string | null }) {
  const { t } = useTranslation();
  const overrides = useOverrideHistory(goalId);
  if (overrides.isPending) return <Skeleton className="h-12 w-full" />;
  if (overrides.isError) {
    return (
      <p role="alert" className="font-mono text-[10px] uppercase tracking-widest text-danger">
        {t("errors.preview_failed")}
      </p>
    );
  }
  const rows = overrides.data ?? [];
  if (rows.length === 0) {
    return (
      <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
        {t("risk_slider.history_empty")}
      </p>
    );
  }
  return (
    <ul className="flex flex-col divide-y divide-hairline">
      {rows.map((row) => (
        <li key={row.id} className="flex flex-col gap-0.5 py-2">
          <span className="font-mono text-[11px] uppercase tracking-wider text-ink">
            {t("risk_slider.history_score", {
              descriptor: row.descriptor,
              score: row.score_1_5,
            })}
          </span>
          <span className="font-mono text-[9px] uppercase tracking-widest text-muted">
            {t("risk_slider.history_meta", {
              actor: row.created_by,
              timestamp: new Date(row.created_at).toLocaleString(),
            })}
          </span>
          <span className="font-sans text-[11px] italic text-muted">{row.rationale}</span>
        </li>
      ))}
    </ul>
  );
}

function CtxSection({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <section className="mb-4 last:mb-0">
      <p className="mb-1.5 font-mono text-[9px] uppercase tracking-widest text-muted">{label}</p>
      {children}
    </section>
  );
}
