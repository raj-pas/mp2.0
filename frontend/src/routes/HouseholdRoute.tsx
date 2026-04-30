import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { useRememberedClientId } from "../chrome/ClientPicker";
import { type GroupByMode } from "../chrome/ModeToggle";
import { Skeleton } from "../components/ui/skeleton";
import { householdExternalAum, householdInternalAum, useHousehold } from "../lib/household";
import { useLocalStorage } from "../lib/local-storage";
import { formatCad, formatCadCompact, formatPct } from "../lib/format";
import { descriptorFor } from "../lib/risk";
import { useTreemap, type TreemapMode } from "../lib/treemap";
import { Treemap } from "../treemap/Treemap";

const STORAGE_GROUP_BY = "mp20_group_by";

function topbarToTreemapMode(mode: GroupByMode): TreemapMode {
  return mode === "by-account" ? "by_account" : "by_goal";
}

export function HouseholdRoute() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [rememberedId] = useRememberedClientId();
  const [groupBy] = useLocalStorage<GroupByMode>(STORAGE_GROUP_BY, "by-account");

  const householdQuery = useHousehold(rememberedId);
  const treemapMode = topbarToTreemapMode(groupBy);
  const treemapQuery = useTreemap(rememberedId, treemapMode);

  if (rememberedId === null) {
    return <HouseholdEmpty message={t("routes.household.select_first")} />;
  }

  if (householdQuery.isPending) {
    return (
      <main className="flex flex-1 flex-col gap-3 bg-paper p-5">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-[calc(100%-4.5rem)] w-full" />
      </main>
    );
  }

  if (householdQuery.isError || householdQuery.data === undefined) {
    return <HouseholdEmpty message={t("routes.household.missing_client")} tone="danger" />;
  }

  const household = householdQuery.data;
  const internalAum = householdInternalAum(household);
  const externalAum = householdExternalAum(household);
  const totalAum = internalAum + externalAum;
  const internalPct = totalAum > 0 ? internalAum / totalAum : 0;
  const externalPct = totalAum > 0 ? externalAum / totalAum : 0;
  const descriptor = descriptorFor(household.household_risk_score, t);

  return (
    <main className="flex flex-1 flex-col gap-3 overflow-hidden bg-paper p-5">
      <section
        className="flex flex-shrink-0 items-center gap-6 border border-hairline-2 bg-paper-2 px-5 py-3 shadow-sm"
        aria-label={t("routes.household.aum_label")}
      >
        <Stat
          label={t("routes.household.aum_label")}
          primary={formatCad(totalAum)}
          secondary={formatCadCompact(totalAum)}
        />
        <AumSplitBar internalPct={internalPct} externalPct={externalPct} />
        <Stat
          label={t("routes.household.aum_internal")}
          primary={formatCad(internalAum)}
          secondary={formatPct(internalPct, 0, { multiply100: true })}
        />
        <Stat
          label={t("routes.household.aum_external")}
          primary={
            externalAum > 0 ? formatCad(externalAum) : t("routes.household.aum_external_pending")
          }
          secondary={externalAum > 0 ? formatPct(externalPct, 0, { multiply100: true }) : undefined}
        />
        <div className="ml-auto flex items-center gap-6">
          <Stat
            label={t("routes.household.risk_score_label")}
            primary={descriptor ?? t("routes.household.risk_score_unset")}
            secondary={
              household.household_risk_score !== null
                ? `${household.household_risk_score} / 5`
                : undefined
            }
          />
          <Stat label={t("routes.household.goals_label")} primary={String(household.goal_count)} />
          <Stat
            label={t("routes.household.accounts_label")}
            primary={String(household.accounts.length)}
          />
        </div>
      </section>

      <section className="flex flex-1 overflow-hidden border border-hairline-2 shadow-sm">
        {treemapQuery.isPending && (
          <div className="flex-1 bg-paper-2 p-3">
            <Skeleton className="h-full w-full" />
          </div>
        )}
        {treemapQuery.isError && (
          <div className="flex-1 bg-paper-2 p-3">
            <p className="font-mono text-[10px] uppercase tracking-widest text-danger">
              {t("errors.preview_failed")}
            </p>
          </div>
        )}
        {treemapQuery.isSuccess && (
          <Treemap
            root={treemapQuery.data.data}
            mode={treemapMode}
            onSelect={(node) => {
              if (treemapMode === "by_account") {
                const accountId = node.id.includes(":") ? node.id.split(":")[0] : node.id;
                if (accountId !== undefined && accountId.length > 0) {
                  navigate(`/account/${encodeURIComponent(accountId)}`);
                }
              } else if (treemapMode === "by_goal") {
                const goalId = node.id.includes(":") ? node.id.split(":")[0] : node.id;
                if (goalId !== undefined && goalId.length > 0) {
                  navigate(`/goal/${encodeURIComponent(goalId)}`);
                }
              }
            }}
          />
        )}
      </section>
    </main>
  );
}

function HouseholdEmpty({
  message,
  tone = "muted",
}: {
  message: string;
  tone?: "muted" | "danger";
}) {
  const className =
    tone === "danger"
      ? "font-mono text-[10px] uppercase tracking-widest text-danger"
      : "font-mono text-[10px] uppercase tracking-widest text-muted";
  return (
    <main className="flex flex-1 items-center justify-center bg-paper">
      <p className={className} role={tone === "danger" ? "alert" : "status"}>
        {message}
      </p>
    </main>
  );
}

function Stat({
  label,
  primary,
  secondary,
}: {
  label: string;
  primary: string;
  secondary?: string | undefined;
}) {
  return (
    <div className="flex flex-col">
      <span className="font-mono text-[9px] uppercase tracking-widest text-muted">{label}</span>
      <span className="font-serif text-lg font-medium text-ink">{primary}</span>
      {secondary !== undefined && (
        <span className="font-mono text-[10px] text-accent-2">{secondary}</span>
      )}
    </div>
  );
}

function AumSplitBar({ internalPct, externalPct }: { internalPct: number; externalPct: number }) {
  return (
    <div className="flex h-2 w-32 overflow-hidden border border-hairline" aria-hidden>
      <span style={{ width: `${internalPct * 100}%`, background: "#0E1116" }} />
      <span style={{ width: `${externalPct * 100}%`, background: "#8B5E3C" }} />
    </div>
  );
}
