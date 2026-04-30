/**
 * Household History tab — list of HouseholdSnapshots newest first
 * with Compare and Restore affordances per row.
 *
 * Locked decision per R1: HouseholdSnapshot is append-only. "Restore"
 * does not rewind — it creates a new snapshot tagged `restore` and
 * rolls the GoalAccountLink amounts back to the chosen state.
 *
 * Vocabulary discipline (canon §6.3a): the row labels are surfaced
 * verbatim from the snapshot (`label` field on the API). UI strings
 * here use canon vocab — "Compare" / "Restore" / "Snapshot" — never
 * "transfer" / "reallocation".
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/button";
import { Skeleton } from "../components/ui/skeleton";
import { CompareScreen } from "../modals/CompareScreen";
import { useRememberedClientId } from "../chrome/ClientPicker";
import { type SnapshotListRow, useRestoreSnapshot, useSnapshots } from "../lib/realignment";
import { formatCadCompact } from "../lib/format";
import { normalizeApiError } from "../lib/api-error";
import { toastError, toastSuccess } from "../lib/toast";

export function HouseholdHistoryTab() {
  const { t } = useTranslation();
  const [rememberedId] = useRememberedClientId();
  const snapshots = useSnapshots(rememberedId);
  const restore = useRestoreSnapshot(rememberedId);
  const [compareSnapshotId, setCompareSnapshotId] = useState<number | null>(null);

  if (rememberedId === null) {
    return (
      <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
        {t("routes.household.select_first")}
      </p>
    );
  }
  if (snapshots.isPending) return <Skeleton className="h-32 w-full" />;
  if (snapshots.isError) {
    return (
      <p role="alert" className="font-mono text-[10px] uppercase tracking-widest text-danger">
        {t("errors.preview_failed")}
      </p>
    );
  }
  const rows = snapshots.data ?? [];
  if (rows.length === 0) {
    return (
      <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
        {t("empty.no_snapshots")}
      </p>
    );
  }

  const newest = rows[0]?.id ?? null;

  return (
    <div className="flex flex-col gap-2">
      <ul className="flex flex-col divide-y divide-hairline">
        {rows.map((row) => (
          <SnapshotRow
            key={row.id}
            row={row}
            currentNewestId={newest}
            onCompare={() => setCompareSnapshotId(row.id)}
            onRestore={() =>
              restore.mutate(
                { snapshotId: row.id },
                {
                  onSuccess: () => {
                    toastSuccess(
                      t("history.restore_success_title"),
                      t("history.restore_success_body"),
                    );
                  },
                  onError: (err) => {
                    const e = normalizeApiError(err, t("history.restore_error"));
                    toastError(t("history.restore_error"), { description: e.message });
                  },
                },
              )
            }
            restoring={restore.isPending && restore.variables?.snapshotId === row.id}
          />
        ))}
      </ul>

      <CompareScreen
        open={compareSnapshotId !== null}
        onOpenChange={(open) => {
          if (!open) setCompareSnapshotId(null);
        }}
        householdId={rememberedId}
        beforeSnapshotId={compareSnapshotId}
        afterSnapshotId={newest}
        title={t("history.compare_title")}
      />
    </div>
  );
}

function SnapshotRow({
  row,
  currentNewestId,
  onCompare,
  onRestore,
  restoring,
}: {
  row: SnapshotListRow;
  currentNewestId: number | null;
  onCompare: () => void;
  onRestore: () => void;
  restoring: boolean;
}) {
  const { t } = useTranslation();
  const isCurrent = row.id === currentNewestId;
  return (
    <li className="flex flex-col gap-1 py-2">
      <div className="flex items-baseline justify-between">
        <span className="font-sans text-[12px] font-medium text-ink">{row.label}</span>
        <span className="font-mono text-[9px] uppercase tracking-widest text-accent-2">
          {row.triggered_by}
        </span>
      </div>
      <div className="flex items-baseline justify-between font-mono text-[10px]">
        <span className="text-muted">
          {new Date(row.created_at).toLocaleString()} · {row.created_by}
        </span>
        <span className="text-ink">
          {t("history.row_metrics", {
            aum: formatCadCompact(row.summary.total_aum),
            score: row.summary.blended_score.toFixed(2),
          })}
        </span>
      </div>
      <div className="mt-1 flex items-center gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onCompare}
          disabled={isCurrent}
          aria-label={t("history.compare_action")}
        >
          {t("history.compare_action")}
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onRestore}
          disabled={restoring || isCurrent}
          aria-label={t("history.restore_action")}
        >
          {restoring ? t("history.restoring") : t("history.restore_action")}
        </Button>
      </div>
    </li>
  );
}
