import { Suspense, lazy, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { useRememberedClientId } from "../chrome/ClientPicker";
import { type GroupByMode } from "../chrome/ModeToggle";
import { ToggleCurrentIdeal, useCurrentIdealMode } from "../chrome/ToggleCurrentIdeal";
import { Button } from "../components/ui/button";
import { Skeleton } from "../components/ui/skeleton";
import {
  householdExternalAum,
  householdInternalAum,
  useHousehold,
  type HouseholdDetail,
} from "../lib/household";
import type { TreemapMode, TreemapNode } from "../lib/treemap";
import { useLocalStorage } from "../lib/local-storage";
import { formatCad, formatCadCompact, formatPct } from "../lib/format";
import { descriptorFor } from "../lib/risk";
import { useTreemap } from "../lib/treemap";
import { CompareScreen } from "../modals/CompareScreen";
import { RealignModal } from "../modals/RealignModal";
import { type RealignmentResponse, useRestoreSnapshot } from "../lib/realignment";
import { toastSuccess } from "../lib/toast";
import { Treemap } from "../treemap/Treemap";
import { HouseholdPortfolioPanel } from "./HouseholdPortfolioPanel";
import { UnallocatedBanner } from "./UnallocatedBanner";

/**
 * P13 / §A1.20 bundle code-split — AssignAccountModal lazy-loads on
 * first open (UnallocatedBanner CTA / Treemap unallocated tile click /
 * BlockerBanner ui_action). Until opened, no JS for the modal is shipped.
 */
const AssignAccountModal = lazy(() => import("../modals/AssignAccountModal"));

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
  const [currentIdealMode] = useCurrentIdealMode();

  // Realignment state machine: closed → modal open → on-success → compare-
  // screen open with the freshly-created snapshot pair → user clicks
  // Confirm (close) or Revert (restore the before-snapshot, creating a
  // new "restore" snapshot per locked decision: snapshots are append-only).
  const [realignOpen, setRealignOpen] = useState(false);
  const [latestRealign, setLatestRealign] = useState<RealignmentResponse | null>(null);
  const restoreSnapshot = useRestoreSnapshot(rememberedId);

  // P13 — AssignAccountModal open state. `null` accountId means the
  // modal is closed. Set to a non-null account_id by:
  //   - UnallocatedBanner CTA click  (per §A1.14 #10)
  //   - Treemap virtual unallocated tile click  (per §A1.14 #10 + §A1.51 P12×P13)
  //   - HouseholdPortfolioPanel BlockerBanner "Assign" ui_action  (§A1.51 P11×P13)
  const [assignTargetAccountId, setAssignTargetAccountId] = useState<string | null>(null);

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
          <Button type="button" variant="outline" size="sm" onClick={() => setRealignOpen(true)}>
            {t("realign.cta")}
          </Button>
          {/*
            P7 (plan v20 §A1.35 / §A1.18 LOCKED sub-bar layout): ToggleCurrentIdeal
            sits AFTER existing actions. Disabled with tooltip when no
            PortfolioRun exists yet — guards downstream reads of a null
            recommended allocation. Persistence is per-user global per
            §A1.14 #14 (no household-id namespace).
          */}
          <ToggleCurrentIdeal disabled={household.latest_portfolio_run === null} />
        </div>
      </section>

      <RealignModal
        open={realignOpen}
        onOpenChange={setRealignOpen}
        household={household}
        onApplied={(response) => setLatestRealign(response)}
      />
      <CompareScreen
        open={latestRealign !== null}
        onOpenChange={(open) => {
          if (!open) setLatestRealign(null);
        }}
        householdId={household.id}
        beforeSnapshotId={latestRealign?.before_snapshot_id ?? null}
        afterSnapshotId={latestRealign?.after_snapshot_id ?? null}
        title={t("realign.compare_title")}
        onConfirm={() => {
          setLatestRealign(null);
          toastSuccess(t("realign.confirm_success"), t("realign.confirm_body"));
        }}
        onRevert={() => {
          if (latestRealign === null) return;
          restoreSnapshot.mutate(
            { snapshotId: latestRealign.before_snapshot_id },
            {
              onSuccess: () => {
                setLatestRealign(null);
                toastSuccess(t("realign.revert_success"), t("realign.revert_body"));
              },
            },
          );
        }}
        reverting={restoreSnapshot.isPending}
      />

      {/*
        UnallocatedBanner per plan v20 §A1.18 LOCKED layout — sits ABOVE
        the action sub-bar (and HouseholdPortfolioPanel). P12 fills the
        slot first established by P11. Z-order coord: banner z-10 sits
        BELOW sister's StaleRunOverlay z-20. P13 wires the CTA to
        AssignAccountModal pre-focused on the affected account.
      */}
      <UnallocatedBanner
        household={household}
        onAssignClick={({ account_id }) => setAssignTargetAccountId(account_id)}
      />

      {/*
        P13 lazy-loaded AssignAccountModal — open state is managed at the
        route level so the same modal handles UnallocatedBanner CTA +
        Treemap unallocated tile click + HouseholdPortfolioPanel
        BlockerBanner "Assign" ui_action (§A1.51 cross-phase contract).
        Suspense fallback is null since the chunk is small (~6 kB) and
        the trigger interactions are click-instigated (not on-load).
      */}
      <Suspense fallback={null}>
        <AssignAccountModal
          open={assignTargetAccountId !== null}
          onOpenChange={(o) => {
            if (!o) setAssignTargetAccountId(null);
          }}
          household={household}
          accountId={assignTargetAccountId}
          onAssigned={() => {
            toastSuccess(
              t("assign_account.toast_success_title"),
              t("assign_account.toast_success_body"),
            );
          }}
        />
      </Suspense>
      {/*
        Backwards-compat stub: the previous P11 placeholder div still
        exists for any structural test that asserts the slot exists by
        test-id. Removed entirely once UnallocatedBanner lifts to GA.
      */}
      <div data-testid="unallocated-banner-slot" hidden aria-hidden="true" />

      <HouseholdPortfolioPanel
        household={household}
        onAssignAccountClick={({ account_id }) => setAssignTargetAccountId(account_id)}
      />

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
            root={
              currentIdealMode === "ideal"
                ? buildIdealTreemapRoot(household, treemapMode)
                : treemapQuery.data.data
            }
            mode={treemapMode}
            dataset={currentIdealMode}
            onSelect={(node) => {
              // Plan v20 §A1.36 (P12) + §A1.14 #10 + §A1.51 P12×P13:
              // unallocated tile clicks open AssignAccountModal
              // pre-focused on the account.
              if (node.unallocated === true) {
                const targetAccountId = node.account_id ?? null;
                if (targetAccountId !== null && targetAccountId.length > 0) {
                  setAssignTargetAccountId(targetAccountId);
                }
                return;
              }
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

/**
 * P7 — derive the "ideal" treemap root from `latest_portfolio_run`.
 * Mirrors the by_account / by_goal shape produced by the
 * `/api/treemap/` endpoint so the Treemap component renders without
 * needing a parallel API. Returns an empty root when the household has
 * no PortfolioRun yet — the Treemap empty-state branch then renders
 * the "No recommendation yet" copy via `dataset="ideal"`.
 */
function buildIdealTreemapRoot(
  household: HouseholdDetail,
  mode: TreemapMode,
): TreemapNode {
  const empty: TreemapNode = {
    id: household.id,
    label: household.display_name,
    children: [],
  };
  const run = household.latest_portfolio_run;
  if (run === null || run.output === null) return empty;
  if (mode === "by_account") {
    const children: TreemapNode[] = run.output.account_rollups.map((rollup) => ({
      id: rollup.id,
      label: rollup.name,
      children: rollup.allocations
        .filter((a) => a.weight > 0)
        .map((a) => ({
          id: `${rollup.id}:${a.sleeve_id}`,
          label: a.sleeve_name,
          value: rollup.allocated_amount * a.weight,
        })),
    }));
    return { id: household.id, label: household.display_name, children };
  }
  if (mode === "by_goal") {
    const children: TreemapNode[] = run.output.goal_rollups.map((rollup) => ({
      id: rollup.id,
      label: rollup.name,
      children: rollup.allocations
        .filter((a) => a.weight > 0)
        .map((a) => ({
          id: `${rollup.id}:${a.sleeve_id}`,
          label: a.sleeve_name,
          value: rollup.allocated_amount * a.weight,
        })),
    }));
    return { id: household.id, label: household.display_name, children };
  }
  return empty;
}
