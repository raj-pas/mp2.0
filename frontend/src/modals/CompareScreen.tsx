/**
 * Side-by-side compare screen — used for both:
 *   - realignment confirm/revert (post-Apply)
 *   - history-tab restore preview
 *
 * Locks the canon §6.3a vocabulary: this is a "compare" of the two
 * snapshots, never a diff between "before transfer" and "after". The
 * Δ column shows allocation deltas, not money movement.
 */
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "../components/ui/dialog";
import { Skeleton } from "../components/ui/skeleton";
import { type SnapshotDetail, type SnapshotSummary, useSnapshot } from "../lib/realignment";
import { formatCad } from "../lib/format";
import { cn } from "../lib/cn";

interface CompareScreenProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  householdId: string;
  /** Snapshot to use as the "before" baseline. */
  beforeSnapshotId: number | null;
  /** Snapshot to use as the "after" comparison. */
  afterSnapshotId: number | null;
  /** Title — typically "Compare" / "Confirm realignment" / "Restore preview". */
  title: string;
  /**
   * Optional confirmation handler. When set the screen renders a Confirm +
   * Revert pair; when omitted only Close is shown.
   *
   *   - `onConfirm()` — keep the after-state (no-op for snapshots-only
   *     compares; meaningful for realignment-just-applied flow).
   *   - `onRevert()` — restore the before-snapshot via the restore mutation.
   */
  onConfirm?: () => void;
  onRevert?: () => void;
  /** Loading flag for the revert mutation. */
  reverting?: boolean;
}

export function CompareScreen({
  open,
  onOpenChange,
  householdId,
  beforeSnapshotId,
  afterSnapshotId,
  title,
  onConfirm,
  onRevert,
  reverting = false,
}: CompareScreenProps) {
  const { t } = useTranslation();
  const before = useSnapshot(householdId, beforeSnapshotId);
  const after = useSnapshot(householdId, afterSnapshotId);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent fullScreen className="p-6">
        <DialogTitle asChild>
          <h2 className="font-serif text-2xl font-medium tracking-tight text-ink">{title}</h2>
        </DialogTitle>
        <DialogDescription asChild>
          <p className="mt-1 text-[12px] text-muted">{t("compare.intro")}</p>
        </DialogDescription>

        <section className="mt-5 grid grid-cols-2 gap-4">
          <SnapshotColumn
            title={t("compare.col_before")}
            data={before.data}
            loading={before.isPending}
            error={before.isError}
          />
          <SnapshotColumn
            title={t("compare.col_after")}
            data={after.data}
            loading={after.isPending}
            error={after.isError}
            counterpart={before.data}
          />
        </section>

        <footer className="mt-6 flex items-center justify-end gap-2 border-t border-hairline pt-4">
          <DialogPrimitive.Close asChild>
            <Button type="button" variant="outline" size="sm">
              {t("common.close")}
            </Button>
          </DialogPrimitive.Close>
          {onRevert !== undefined && (
            <Button
              type="button"
              variant="destructive"
              size="sm"
              onClick={onRevert}
              disabled={reverting}
            >
              {reverting ? t("compare.reverting") : t("compare.revert")}
            </Button>
          )}
          {onConfirm !== undefined && (
            <Button
              type="button"
              size="sm"
              onClick={() => {
                onConfirm();
                onOpenChange(false);
              }}
            >
              {t("compare.confirm")}
            </Button>
          )}
        </footer>
      </DialogContent>
    </Dialog>
  );
}

function SnapshotColumn({
  title,
  data,
  loading,
  error,
  counterpart,
}: {
  title: string;
  data: SnapshotDetail | undefined;
  loading: boolean;
  error: boolean;
  counterpart?: SnapshotDetail | undefined;
}) {
  const { t } = useTranslation();
  return (
    <section
      className="flex flex-col gap-4 border border-hairline-2 bg-paper-2 p-4"
      aria-label={title}
    >
      <header className="flex items-baseline justify-between">
        <h3 className="font-mono text-[10px] uppercase tracking-widest text-muted">{title}</h3>
        {data !== undefined && (
          <span className="font-mono text-[10px] text-muted">
            {new Date(data.created_at).toLocaleString()}
          </span>
        )}
      </header>
      {loading && <Skeleton className="h-32 w-full" />}
      {error && (
        <p role="alert" className="font-mono text-[10px] uppercase tracking-widest text-danger">
          {t("errors.preview_failed")}
        </p>
      )}
      {data !== undefined && (
        <>
          <SummaryRows summary={data.summary} counterpart={counterpart?.summary} />
          <PerGoalRows snapshot={data} counterpart={counterpart} />
        </>
      )}
    </section>
  );
}

function SummaryRows({
  summary,
  counterpart,
}: {
  summary: SnapshotSummary;
  counterpart?: SnapshotSummary | undefined;
}) {
  const { t } = useTranslation();
  const rows: { label: string; value: string; delta?: string }[] = [
    {
      label: t("compare.summary_total_aum"),
      value: formatCad(summary.total_aum),
      delta:
        counterpart !== undefined
          ? formatSignedCad(summary.total_aum - counterpart.total_aum)
          : undefined,
    },
    {
      label: t("compare.summary_blended"),
      value: summary.blended_score.toFixed(2),
      delta:
        counterpart !== undefined
          ? formatSignedNumber(summary.blended_score - counterpart.blended_score)
          : undefined,
    },
    {
      label: t("compare.summary_goal_count"),
      value: String(summary.goal_count),
      delta:
        counterpart !== undefined
          ? formatSignedNumber(summary.goal_count - counterpart.goal_count)
          : undefined,
    },
    {
      label: t("compare.summary_account_count"),
      value: String(summary.account_count),
      delta:
        counterpart !== undefined
          ? formatSignedNumber(summary.account_count - counterpart.account_count)
          : undefined,
    },
  ];
  return (
    <dl className="flex flex-col gap-1.5">
      {rows.map((row) => (
        <div key={row.label} className="flex items-baseline justify-between gap-3">
          <dt className="font-mono text-[10px] uppercase tracking-widest text-muted">
            {row.label}
          </dt>
          <dd className="flex items-baseline gap-2 font-serif text-[14px] text-ink">
            <span>{row.value}</span>
            {row.delta !== undefined && row.delta !== "—" && <DeltaBadge delta={row.delta} />}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function PerGoalRows({
  snapshot,
  counterpart,
}: {
  snapshot: SnapshotDetail;
  counterpart?: SnapshotDetail | undefined;
}) {
  const { t } = useTranslation();
  const goals = (snapshot.snapshot.goals ?? []) as GoalSnapshot[];
  if (goals.length === 0) {
    return (
      <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
        {t("compare.no_goals")}
      </p>
    );
  }
  const counterMap = buildGoalMap(counterpart?.snapshot.goals as GoalSnapshot[] | undefined);
  return (
    <div className="border-t border-hairline pt-3">
      <p className="mb-2 font-mono text-[9px] uppercase tracking-widest text-muted">
        {t("compare.per_goal_title")}
      </p>
      <ul className="flex flex-col gap-1">
        {goals.map((goal) => {
          const totalAllocated = sumLegs(goal);
          const peer = counterMap[goal.external_id];
          const counterTotal = peer !== undefined ? sumLegs(peer) : null;
          return (
            <li
              key={goal.external_id}
              className="flex items-baseline justify-between gap-3 font-mono text-[11px]"
            >
              <span className="text-ink">{goal.name ?? goal.external_id}</span>
              <span className="flex items-baseline gap-2">
                <span className="text-accent-2">{formatCad(totalAllocated)}</span>
                {counterTotal !== null && (
                  <DeltaBadge delta={formatSignedCad(totalAllocated - counterTotal)} />
                )}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function DeltaBadge({ delta }: { delta: string }) {
  const positive = delta.startsWith("+");
  const negative = delta.startsWith("-") && !delta.startsWith("-0");
  return (
    <span
      className={cn(
        "border px-1.5 py-0.5 font-mono text-[10px]",
        positive
          ? "border-success/40 text-success"
          : negative
            ? "border-danger/40 text-danger"
            : "border-hairline text-muted",
      )}
    >
      {delta}
    </span>
  );
}

type GoalSnapshot = {
  external_id: string;
  name?: string;
  account_allocations?: { allocated_amount?: number | string }[];
  legs?: { allocated_amount?: number | string }[];
};

function buildGoalMap(goals: GoalSnapshot[] | undefined): Record<string, GoalSnapshot> {
  if (goals === undefined) return {};
  const map: Record<string, GoalSnapshot> = {};
  for (const goal of goals) {
    map[goal.external_id] = goal;
  }
  return map;
}

function sumLegs(goal: GoalSnapshot): number {
  const legs = goal.account_allocations ?? goal.legs ?? [];
  return legs.reduce((sum, leg) => sum + Number(leg?.allocated_amount ?? 0), 0);
}

function formatSignedCad(value: number): string {
  if (Math.abs(value) < 0.5) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${formatCad(value)}`;
}

function formatSignedNumber(value: number): string {
  if (Math.abs(value) < 0.005) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}`;
}
