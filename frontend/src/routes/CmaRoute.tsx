/**
 * CMA Workbench (Phase R9 — analyst-only).
 *
 * Five tabs surfacing the existing CMA backend (canon §4.1 + locked
 * decision #5):
 *   1. Snapshots — list (active / drafts / archived) + "Create draft"
 *   2. Assumptions — per-fund expected_return / volatility editor
 *   3. Correlations — symmetric correlation-matrix editor
 *   4. Frontier — Chart.js efficient-frontier viewer
 *   5. Audit — recent CMA audit events
 *
 * RBAC: financial-analyst-only. The advisor role gets a `403 — Only
 * financial analysts can access CMA snapshots.` from the API; the UI
 * surfaces that loudly so we never silently no-op.
 *
 * Backend: unchanged. Same 6 endpoints (list, detail, active, audit,
 * publish, frontier) that have shipped since the post-Phase-1 CMA
 * Workbench. R9 is a UI rebuild only.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/button";
import { Skeleton } from "../components/ui/skeleton";
import { ApiError } from "../lib/api";
import { cn } from "../lib/cn";
import {
  type CmaCorrelation,
  type CmaFundAssumption,
  type CmaSnapshot,
  type CmaSnapshotStatus,
  useCmaActiveSnapshot,
  useCmaAuditLog,
  useCmaFrontier,
  useCmaSnapshot,
  useCmaSnapshots,
  useCreateCmaDraft,
  usePatchCmaSnapshot,
  usePublishCmaSnapshot,
} from "../lib/cma";
import { formatPct } from "../lib/format";
import { toastError, toastSuccess } from "../lib/toast";

type TabKey = "snapshots" | "assumptions" | "correlations" | "frontier" | "audit";

const TAB_KEYS: TabKey[] = ["snapshots", "assumptions", "correlations", "frontier", "audit"];

export function CmaRoute() {
  const { t } = useTranslation();
  const snapshotsQuery = useCmaSnapshots();
  const activeQuery = useCmaActiveSnapshot();

  const [activeTab, setActiveTab] = useState<TabKey>("snapshots");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Default-select the active snapshot so the editor tabs have data
  // immediately when the analyst lands.
  useEffect(() => {
    if (selectedId !== null) return;
    const active = activeQuery.data;
    if (active) {
      setSelectedId(active.external_id);
    }
  }, [selectedId, activeQuery.data]);

  const selectedQuery = useCmaSnapshot(selectedId);
  const isAnalystForbidden =
    snapshotsQuery.error instanceof ApiError && snapshotsQuery.error.status === 403;

  if (isAnalystForbidden) {
    return (
      <main className="flex flex-1 items-center justify-center bg-paper">
        <div className="max-w-md text-center">
          <h1 className="font-serif text-2xl text-ink">{t("cma.heading")}</h1>
          <p className="mt-3 text-[13px] text-muted">{t("cma.forbidden_body")}</p>
        </div>
      </main>
    );
  }

  return (
    <main className="flex flex-1 flex-col overflow-hidden bg-paper">
      <CmaHeader
        active={activeQuery.data}
        snapshots={snapshotsQuery.data ?? []}
        selectedId={selectedId}
        onSelectSnapshot={(id) => {
          setSelectedId(id);
          if (activeTab === "snapshots") setActiveTab("assumptions");
        }}
      />
      <CmaTabBar activeTab={activeTab} onChange={setActiveTab} />
      <div className="flex-1 overflow-y-auto px-8 py-6">
        {activeTab === "snapshots" && (
          <SnapshotsTab
            snapshots={snapshotsQuery.data ?? []}
            isLoading={snapshotsQuery.isLoading}
            isError={Boolean(snapshotsQuery.error)}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        )}
        {activeTab === "assumptions" && (
          <AssumptionsTab
            snapshot={selectedQuery.data ?? null}
            isLoading={selectedQuery.isLoading || (selectedId === null && activeQuery.isLoading)}
          />
        )}
        {activeTab === "correlations" && (
          <CorrelationsTab
            snapshot={selectedQuery.data ?? null}
            isLoading={selectedQuery.isLoading || (selectedId === null && activeQuery.isLoading)}
          />
        )}
        {activeTab === "frontier" && (
          <FrontierTab snapshotId={selectedId} snapshotName={selectedQuery.data?.name ?? ""} />
        )}
        {activeTab === "audit" && <AuditTab />}
      </div>
    </main>
  );
}

// ---------------------------------------------------------------------------
// Header — title + active-snapshot pill + create-draft action
// ---------------------------------------------------------------------------

interface HeaderProps {
  active: CmaSnapshot | undefined;
  snapshots: CmaSnapshot[];
  selectedId: string | null;
  onSelectSnapshot: (id: string) => void;
}

function CmaHeader({ active, snapshots, selectedId, onSelectSnapshot }: HeaderProps) {
  const { t } = useTranslation();
  const createDraft = useCreateCmaDraft();
  const draftExists = snapshots.some((s) => s.status === "draft");

  function handleCreate() {
    if (!active) {
      toastError(t("cma.no_active_for_draft"));
      return;
    }
    createDraft.mutate(
      { copy_from_snapshot_id: active.external_id },
      {
        onSuccess: (snapshot) => {
          onSelectSnapshot(snapshot.external_id);
          toastSuccess(t("cma.draft_created", { version: snapshot.version }));
        },
        onError: (err) => {
          toastError(err instanceof Error ? err.message : t("cma.draft_create_failed"));
        },
      },
    );
  }

  return (
    <header className="flex items-center justify-between border-b border-hairline-2 bg-paper-2 px-8 py-4">
      <div className="flex items-baseline gap-4">
        <h1 className="font-serif text-2xl font-medium tracking-tight text-ink">
          {t("cma.heading")}
        </h1>
        {active && (
          <span className="font-mono text-[10px] uppercase tracking-widest text-muted">
            {t("cma.active_label", { name: active.name, version: active.version })}
          </span>
        )}
      </div>
      <div className="flex items-center gap-3">
        {selectedId && active?.external_id !== selectedId && (
          <span className="font-mono text-[10px] uppercase tracking-widest text-accent-2">
            {t("cma.editing_label")}
          </span>
        )}
        <Button
          type="button"
          variant="default"
          onClick={handleCreate}
          disabled={createDraft.isPending || draftExists}
        >
          {draftExists ? t("cma.draft_exists") : t("cma.create_draft")}
        </Button>
      </div>
    </header>
  );
}

// ---------------------------------------------------------------------------
// Tab bar
// ---------------------------------------------------------------------------

function CmaTabBar({
  activeTab,
  onChange,
}: {
  activeTab: TabKey;
  onChange: (tab: TabKey) => void;
}) {
  const { t } = useTranslation();
  return (
    <div
      role="tablist"
      aria-label={t("cma.tablist_label")}
      className="flex border-b border-hairline-2 bg-paper-2 px-8"
    >
      {TAB_KEYS.map((tab) => {
        const isActive = tab === activeTab;
        return (
          <button
            key={tab}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab)}
            className={cn(
              "border-b-2 px-4 py-2 font-mono text-[11px] uppercase tracking-widest transition-colors",
              isActive
                ? "border-accent text-ink"
                : "border-transparent text-muted hover:text-ink",
            )}
          >
            {t(`cma.tab.${tab}`)}
          </button>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Snapshots tab — list of all CMA snapshots with status pills.
// ---------------------------------------------------------------------------

function SnapshotsTab({
  snapshots,
  isLoading,
  isError,
  selectedId,
  onSelect,
}: {
  snapshots: CmaSnapshot[];
  isLoading: boolean;
  isError: boolean;
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const { t } = useTranslation();

  if (isLoading) {
    return <Skeleton className="h-40 w-full" />;
  }
  if (isError) {
    return (
      <p role="alert" className="text-[13px] text-danger">
        {t("cma.snapshots_load_error")}
      </p>
    );
  }
  if (snapshots.length === 0) {
    return <p className="text-[13px] text-muted">{t("cma.no_snapshots")}</p>;
  }

  const sorted = [...snapshots].sort((a, b) => b.version - a.version);

  return (
    <table className="w-full text-left text-[12px]">
      <thead>
        <tr className="border-b border-hairline">
          <th className="py-2 pr-4 font-mono text-[10px] uppercase tracking-widest text-muted">
            {t("cma.col.version")}
          </th>
          <th className="py-2 pr-4 font-mono text-[10px] uppercase tracking-widest text-muted">
            {t("cma.col.name")}
          </th>
          <th className="py-2 pr-4 font-mono text-[10px] uppercase tracking-widest text-muted">
            {t("cma.col.status")}
          </th>
          <th className="py-2 pr-4 font-mono text-[10px] uppercase tracking-widest text-muted">
            {t("cma.col.published")}
          </th>
          <th className="py-2 font-mono text-[10px] uppercase tracking-widest text-muted">
            {t("cma.col.actions")}
          </th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((snapshot) => (
          <tr key={snapshot.external_id} className="border-b border-hairline">
            <td className="py-2 pr-4 font-mono tabular-nums text-ink">
              {t("cma.version_value", { version: snapshot.version })}
            </td>
            <td className="py-2 pr-4 text-ink">{snapshot.name}</td>
            <td className="py-2 pr-4">
              <StatusPill status={snapshot.status} />
            </td>
            <td className="py-2 pr-4 font-mono tabular-nums text-muted">
              {snapshot.published_at
                ? new Date(snapshot.published_at).toISOString().slice(0, 10)
                : "—"}
            </td>
            <td className="py-2">
              <Button
                type="button"
                variant={snapshot.external_id === selectedId ? "default" : "outline"}
                size="sm"
                onClick={() => onSelect(snapshot.external_id)}
              >
                {snapshot.external_id === selectedId ? t("cma.selected") : t("cma.select")}
              </Button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function StatusPill({ status }: { status: CmaSnapshotStatus }) {
  const { t } = useTranslation();
  const className = cn(
    "inline-flex items-center px-2 py-0.5 font-mono text-[9px] uppercase tracking-widest",
    status === "active" && "bg-success/20 text-success",
    status === "draft" && "bg-accent/20 text-accent-2",
    status === "archived" && "bg-paper-2 text-muted",
  );
  return <span className={className}>{t(`cma.status.${status}`)}</span>;
}

// ---------------------------------------------------------------------------
// Assumptions tab — per-fund expected_return / volatility editor.
// ---------------------------------------------------------------------------

function AssumptionsTab({
  snapshot,
  isLoading,
}: {
  snapshot: CmaSnapshot | null;
  isLoading: boolean;
}) {
  const { t } = useTranslation();
  const patchMutation = usePatchCmaSnapshot(snapshot?.external_id ?? null);
  const publishMutation = usePublishCmaSnapshot(snapshot?.external_id ?? null);
  const [drafts, setDrafts] = useState<Record<string, { er: string; vol: string }>>({});
  const [publishNote, setPublishNote] = useState("");

  if (isLoading) {
    return <Skeleton className="h-64 w-full" />;
  }
  if (!snapshot) {
    return <p className="text-[13px] text-muted">{t("cma.select_snapshot_first")}</p>;
  }

  const isDraft = snapshot.status === "draft";
  const sortedFunds = [...snapshot.fund_assumptions].sort(
    (a, b) => a.display_order - b.display_order,
  );

  function valueFor(fund: CmaFundAssumption, field: "er" | "vol"): string {
    const draft = drafts[fund.fund_id];
    if (draft) return draft[field];
    return field === "er" ? fund.expected_return : fund.volatility;
  }

  function onChange(fundId: string, field: "er" | "vol", value: string) {
    setDrafts((prev) => {
      const fund = sortedFunds.find((f) => f.fund_id === fundId);
      if (!fund) return prev;
      const current = prev[fundId] ?? { er: fund.expected_return, vol: fund.volatility };
      return { ...prev, [fundId]: { ...current, [field]: value } };
    });
  }

  function handleSave() {
    const fundUpdates = Object.entries(drafts).map(([fund_id, draft]) => ({
      fund_id,
      expected_return: draft.er,
      volatility: draft.vol,
    }));
    if (fundUpdates.length === 0) {
      toastError(t("cma.no_changes_to_save"));
      return;
    }
    patchMutation.mutate(
      { fund_assumptions: fundUpdates },
      {
        onSuccess: () => {
          toastSuccess(t("cma.assumptions_saved"));
          setDrafts({});
        },
        onError: (err) => {
          toastError(err instanceof Error ? err.message : t("cma.save_failed"));
        },
      },
    );
  }

  function handlePublish() {
    if (!publishNote.trim()) {
      toastError(t("cma.publish_note_required"));
      return;
    }
    publishMutation.mutate(
      { publish_note: publishNote.trim() },
      {
        onSuccess: () => {
          toastSuccess(t("cma.published"));
          setPublishNote("");
        },
        onError: (err) => {
          toastError(err instanceof Error ? err.message : t("cma.publish_failed"));
        },
      },
    );
  }

  const dirty = Object.keys(drafts).length > 0;

  return (
    <div className="flex flex-col gap-4">
      <table className="w-full text-left text-[12px]">
        <thead>
          <tr className="border-b border-hairline">
            <th className="py-2 pr-4 font-mono text-[10px] uppercase tracking-widest text-muted">
              {t("cma.col.fund")}
            </th>
            <th className="py-2 pr-4 font-mono text-[10px] uppercase tracking-widest text-muted">
              {t("cma.col.expected_return")}
            </th>
            <th className="py-2 pr-4 font-mono text-[10px] uppercase tracking-widest text-muted">
              {t("cma.col.volatility")}
            </th>
            <th className="py-2 font-mono text-[10px] uppercase tracking-widest text-muted">
              {t("cma.col.eligible")}
            </th>
          </tr>
        </thead>
        <tbody>
          {sortedFunds.map((fund) => (
            <tr key={fund.fund_id} className="border-b border-hairline">
              <td className="py-2 pr-4 text-ink">
                <span className="font-mono text-[10px] tabular-nums text-muted">
                  {fund.fund_id}
                </span>
                <span className="ml-2">{fund.name}</span>
              </td>
              <td className="py-2 pr-4">
                <input
                  type="number"
                  step="0.0001"
                  value={valueFor(fund, "er")}
                  disabled={!isDraft}
                  onChange={(e) => onChange(fund.fund_id, "er", e.target.value)}
                  aria-label={t("cma.input_er_aria", { fund: fund.name })}
                  className="w-24 border border-hairline bg-paper px-2 py-1 font-mono tabular-nums text-ink disabled:bg-paper-2 disabled:text-muted"
                />
              </td>
              <td className="py-2 pr-4">
                <input
                  type="number"
                  step="0.0001"
                  value={valueFor(fund, "vol")}
                  disabled={!isDraft}
                  onChange={(e) => onChange(fund.fund_id, "vol", e.target.value)}
                  aria-label={t("cma.input_vol_aria", { fund: fund.name })}
                  className="w-24 border border-hairline bg-paper px-2 py-1 font-mono tabular-nums text-ink disabled:bg-paper-2 disabled:text-muted"
                />
              </td>
              <td className="py-2 font-mono text-[10px] tabular-nums text-muted">
                {fund.optimizer_eligible ? "✓" : "—"}
                {fund.is_whole_portfolio && (
                  <span className="ml-2 uppercase tracking-widest">{t("cma.fof_label")}</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {isDraft ? (
        <div className="flex flex-col gap-3 border-t border-hairline-2 pt-4">
          <div className="flex items-center gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={handleSave}
              disabled={!dirty || patchMutation.isPending}
            >
              {patchMutation.isPending ? t("cma.saving") : t("cma.save_assumptions")}
            </Button>
            {dirty && (
              <span className="font-mono text-[10px] uppercase tracking-widest text-accent-2">
                {t("cma.unsaved_changes", { count: Object.keys(drafts).length })}
              </span>
            )}
          </div>
          <div className="flex items-end gap-3">
            <label className="flex flex-col gap-1">
              <span className="font-mono text-[10px] uppercase tracking-widest text-muted">
                {t("cma.publish_note_label")}
              </span>
              <input
                type="text"
                value={publishNote}
                onChange={(e) => setPublishNote(e.target.value)}
                placeholder={t("cma.publish_note_placeholder")}
                className="w-96 border border-hairline bg-paper px-2 py-1 text-[12px] text-ink"
              />
            </label>
            <Button
              type="button"
              variant="default"
              onClick={handlePublish}
              disabled={!publishNote.trim() || publishMutation.isPending || dirty}
            >
              {publishMutation.isPending ? t("cma.publishing") : t("cma.publish")}
            </Button>
          </div>
          {dirty && (
            <p className="text-[11px] text-muted">{t("cma.publish_disabled_dirty")}</p>
          )}
        </div>
      ) : (
        <p className="border-t border-hairline-2 pt-4 text-[11px] text-muted">
          {t("cma.assumptions_readonly")}
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Correlations tab — symmetric matrix editor.
// ---------------------------------------------------------------------------

function CorrelationsTab({
  snapshot,
  isLoading,
}: {
  snapshot: CmaSnapshot | null;
  isLoading: boolean;
}) {
  const { t } = useTranslation();
  const patchMutation = usePatchCmaSnapshot(snapshot?.external_id ?? null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});

  if (isLoading) return <Skeleton className="h-64 w-full" />;
  if (!snapshot) return <p className="text-[13px] text-muted">{t("cma.select_snapshot_first")}</p>;

  const isDraft = snapshot.status === "draft";
  const fundIds = [...snapshot.fund_assumptions]
    .sort((a, b) => a.display_order - b.display_order)
    .map((f) => f.fund_id);
  const snapshotCorrelations = snapshot.correlations;

  function pairKey(row: string, col: string): string {
    return [row, col].sort().join("__");
  }

  function correlationFor(row: string, col: string): string {
    if (row === col) return "1.000000";
    const draft = drafts[pairKey(row, col)];
    if (draft !== undefined) return draft;
    const correlation = snapshotCorrelations.find(
      (c) =>
        (c.row_fund_id === row && c.col_fund_id === col) ||
        (c.row_fund_id === col && c.col_fund_id === row),
    );
    return correlation ? correlation.correlation : "0.000000";
  }

  function onChange(row: string, col: string, value: string) {
    setDrafts((prev) => ({ ...prev, [pairKey(row, col)]: value }));
  }

  function handleSave() {
    const updates: CmaCorrelation[] = [];
    for (const [key, correlation] of Object.entries(drafts)) {
      const [row_fund_id, col_fund_id] = key.split("__");
      if (!row_fund_id || !col_fund_id) continue;
      updates.push({ row_fund_id, col_fund_id, correlation });
    }
    if (updates.length === 0) {
      toastError(t("cma.no_changes_to_save"));
      return;
    }
    patchMutation.mutate(
      { correlations: updates },
      {
        onSuccess: () => {
          toastSuccess(t("cma.correlations_saved"));
          setDrafts({});
        },
        onError: (err) => {
          const message = err instanceof Error ? err.message : t("cma.save_failed");
          toastError(message);
        },
      },
    );
  }

  const dirty = Object.keys(drafts).length > 0;

  return (
    <div className="flex flex-col gap-4">
      <table className="w-full border-collapse text-center text-[11px]">
        <thead>
          <tr>
            <th className="border border-hairline bg-paper-2 px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-muted">
              {t("cma.col.fund")}
            </th>
            {fundIds.map((id) => (
              <th
                key={id}
                className="border border-hairline bg-paper-2 px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-muted"
              >
                {id}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {fundIds.map((row) => (
            <tr key={row}>
              <th
                scope="row"
                className="border border-hairline bg-paper-2 px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-muted"
              >
                {row}
              </th>
              {fundIds.map((col) => {
                const correlation = correlationFor(row, col);
                const isDiagonal = row === col;
                return (
                  <td key={col} className="border border-hairline bg-paper px-1 py-1">
                    {isDiagonal ? (
                      <span className="font-mono tabular-nums text-muted">1.0000</span>
                    ) : (
                      <input
                        type="number"
                        step="0.01"
                        min={-1}
                        max={1}
                        value={correlation}
                        disabled={!isDraft}
                        onChange={(e) => onChange(row, col, e.target.value)}
                        aria-label={t("cma.input_corr_aria", { row, col })}
                        className="w-16 border border-hairline bg-paper px-1 py-0.5 text-center font-mono tabular-nums text-ink disabled:bg-paper-2 disabled:text-muted"
                      />
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      {isDraft ? (
        <div className="flex items-center gap-3 border-t border-hairline-2 pt-4">
          <Button
            type="button"
            variant="outline"
            onClick={handleSave}
            disabled={!dirty || patchMutation.isPending}
          >
            {patchMutation.isPending ? t("cma.saving") : t("cma.save_correlations")}
          </Button>
          {dirty && (
            <span className="font-mono text-[10px] uppercase tracking-widest text-accent-2">
              {t("cma.unsaved_changes", { count: Object.keys(drafts).length })}
            </span>
          )}
        </div>
      ) : (
        <p className="border-t border-hairline-2 pt-4 text-[11px] text-muted">
          {t("cma.correlations_readonly")}
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Frontier tab — Chart.js scatter of efficient frontier.
// ---------------------------------------------------------------------------

function FrontierTab({
  snapshotId,
  snapshotName,
}: {
  snapshotId: string | null;
  snapshotName: string;
}) {
  const { t } = useTranslation();
  const frontierQuery = useCmaFrontier(snapshotId);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const chartRef = useRef<unknown>(null);

  const data = frontierQuery.data;

  useEffect(() => {
    if (!data || !canvasRef.current) return;
    let disposed = false;
    let cleanup: (() => void) | undefined;
    void (async () => {
      const ChartModule = await import("chart.js/auto");
      const Chart = ChartModule.default;
      if (disposed) return;
      const ctx = canvasRef.current?.getContext("2d");
      if (!ctx) return;
      // Cleanup any prior chart instance (tab re-render or new snapshot).
      const existing = chartRef.current as { destroy?: () => void } | null;
      existing?.destroy?.();
      chartRef.current = new Chart(ctx, {
        type: "scatter",
        data: {
          datasets: [
            {
              label: t("cma.frontier_efficient"),
              data: data.efficient.map((p) => ({
                x: p.volatility,
                y: p.expected_return,
              })),
              borderColor: "#0E1116",
              backgroundColor: "#C5A572",
              showLine: true,
              tension: 0.05,
            },
            {
              label: t("cma.frontier_funds"),
              data: data.funds.map((p) => ({
                x: p.volatility,
                y: p.expected_return,
              })),
              borderColor: "#8B5E3C",
              backgroundColor: "rgba(139, 94, 60, 0.6)",
              showLine: false,
              pointRadius: 4,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: {
              title: { display: true, text: t("cma.axis_volatility") },
              grid: { color: "rgba(14, 17, 22, 0.05)" },
            },
            y: {
              title: { display: true, text: t("cma.axis_expected_return") },
              grid: { color: "rgba(14, 17, 22, 0.05)" },
            },
          },
          plugins: {
            legend: { position: "bottom", labels: { font: { size: 10 } } },
            title: {
              display: true,
              text: t("cma.frontier_title", { name: snapshotName }),
            },
          },
        },
      });
      cleanup = () => {
        const live = chartRef.current as { destroy?: () => void } | null;
        live?.destroy?.();
        chartRef.current = null;
      };
    })();
    return () => {
      disposed = true;
      cleanup?.();
    };
  }, [data, snapshotName, t]);

  if (!snapshotId) {
    return <p className="text-[13px] text-muted">{t("cma.select_snapshot_first")}</p>;
  }
  if (frontierQuery.isLoading) return <Skeleton className="h-64 w-full" />;
  if (frontierQuery.error) {
    const message =
      frontierQuery.error instanceof ApiError
        ? frontierQuery.error.message
        : t("cma.frontier_load_error");
    return (
      <p role="alert" className="text-[13px] text-danger">
        {message}
      </p>
    );
  }

  return (
    <div className="flex h-[480px] flex-col gap-2">
      <canvas
        ref={canvasRef}
        aria-label={t("cma.frontier_aria")}
        className="h-full w-full"
      />
      {data && (
        <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
          {t("cma.frontier_points_summary", {
            efficient: data.efficient.length,
            funds: data.funds.length,
          })}
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Audit tab — recent CMA audit events.
// ---------------------------------------------------------------------------

function AuditTab() {
  const { t } = useTranslation();
  const auditQuery = useCmaAuditLog();

  const events = useMemo(() => {
    return auditQuery.data ?? [];
  }, [auditQuery.data]);

  if (auditQuery.isLoading) return <Skeleton className="h-64 w-full" />;
  if (auditQuery.error) {
    return (
      <p role="alert" className="text-[13px] text-danger">
        {t("cma.audit_load_error")}
      </p>
    );
  }
  if (events.length === 0) {
    return <p className="text-[13px] text-muted">{t("cma.audit_empty")}</p>;
  }

  return (
    <ul className="flex flex-col gap-2">
      {events.map((event) => (
        <li
          key={event.id}
          className="flex items-baseline gap-3 border-b border-hairline pb-2 text-[12px]"
        >
          <span className="w-44 font-mono text-[10px] tabular-nums text-muted">
            {new Date(event.created_at).toISOString().replace("T", " ").slice(0, 19)}
          </span>
          <span className="w-56 font-mono text-[10px] uppercase tracking-widest text-accent-2">
            {event.action}
          </span>
          <span className="flex-1 text-ink">
            {t("cma.audit_actor_meta", {
              actor: event.actor || t("cma.audit_actor_system"),
              note: extractAuditNote(event.metadata),
            })}
          </span>
        </li>
      ))}
    </ul>
  );
}

function extractAuditNote(metadata: Record<string, unknown>): string {
  const note = metadata["publish_note"];
  if (typeof note === "string" && note.length > 0) return note;
  const version = metadata["version"];
  if (typeof version === "number") return `v${version}`;
  return "";
}

// Suppress unused warning for formatPct (left in for any future inline format work)
void formatPct;
