import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BarChart3,
  CheckCircle2,
  Database,
  FileText,
  History,
  RefreshCw,
  Save,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import {
  Chart,
  Legend,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  ScatterController,
  Tooltip,
} from "chart.js";

import {
  createCmaDraft,
  fetchCmaAudit,
  fetchCmaFrontier,
  fetchCmaSnapshots,
  publishCmaSnapshot,
  updateCmaSnapshot,
} from "./api";
import { Button } from "./components/ui/button";
import type { CmaAuditEvent, CmaFrontier, CMASnapshot } from "./types";

Chart.register(
  Legend,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  ScatterController,
  Tooltip,
);

type WorkbenchTab = "snapshots" | "assumptions" | "correlations" | "frontier" | "audit";

const percent = new Intl.NumberFormat("en-CA", {
  style: "percent",
  maximumFractionDigits: 1,
});

export function CmaWorkbench() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<WorkbenchTab>("snapshots");
  const [workingDraft, setWorkingDraft] = useState<CMASnapshot | null>(null);
  const [publishNote, setPublishNote] = useState("");
  const snapshots = useQuery({
    queryKey: ["cma-snapshots"],
    queryFn: fetchCmaSnapshots,
  });
  const audit = useQuery({
    queryKey: ["cma-audit"],
    queryFn: fetchCmaAudit,
  });

  const active = snapshots.data?.find((snapshot) => snapshot.status === "active") ?? null;
  const draft = snapshots.data?.find((snapshot) => snapshot.status === "draft") ?? null;
  const selectedSnapshot = workingDraft ?? draft ?? active;
  const validationMessages = useMemo(
    () => (workingDraft ? validateDraft(workingDraft) : []),
    [workingDraft],
  );
  const savedPreviewSnapshot = draft ?? active;
  const frontier = useQuery({
    queryKey: ["cma-frontier", savedPreviewSnapshot?.external_id],
    queryFn: () => fetchCmaFrontier(savedPreviewSnapshot!.external_id),
    enabled: Boolean(savedPreviewSnapshot),
  });
  const hasUnsavedDraft =
    Boolean(workingDraft && draft) && JSON.stringify(workingDraft) !== JSON.stringify(draft);

  useEffect(() => {
    if (draft && workingDraft?.external_id !== draft.external_id) {
      setWorkingDraft(cloneSnapshot(draft));
    }
    if (!draft && workingDraft) {
      setWorkingDraft(null);
    }
  }, [draft, workingDraft]);

  const createDraftMutation = useMutation({
    mutationFn: () => createCmaDraft(active?.external_id ?? ""),
    onSuccess: (snapshot) => {
      setWorkingDraft(cloneSnapshot(snapshot));
      setTab("assumptions");
      void queryClient.invalidateQueries({ queryKey: ["cma-snapshots"] });
    },
  });
  const saveDraftMutation = useMutation({
    mutationFn: (snapshot: CMASnapshot) =>
      updateCmaSnapshot(snapshot.external_id, {
        notes: snapshot.notes,
        fund_assumptions: snapshot.fund_assumptions,
        correlations: snapshot.correlations,
      }),
    onSuccess: (snapshot) => {
      setWorkingDraft(cloneSnapshot(snapshot));
      void queryClient.invalidateQueries({ queryKey: ["cma-snapshots"] });
      void queryClient.invalidateQueries({ queryKey: ["cma-frontier"] });
      void queryClient.invalidateQueries({ queryKey: ["cma-audit"] });
    },
  });
  const publishMutation = useMutation({
    mutationFn: (snapshot: CMASnapshot) => publishCmaSnapshot(snapshot.external_id, publishNote),
    onSuccess: () => {
      setWorkingDraft(null);
      setPublishNote("");
      setTab("snapshots");
      void queryClient.invalidateQueries({ queryKey: ["cma-snapshots"] });
      void queryClient.invalidateQueries({ queryKey: ["cma-frontier"] });
      void queryClient.invalidateQueries({ queryKey: ["cma-audit"] });
    },
  });

  const error =
    snapshots.error ??
    audit.error ??
    frontier.error ??
    createDraftMutation.error ??
    saveDraftMutation.error ??
    publishMutation.error;

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <header className="border-b border-slate-200 pb-4">
        <p className="text-xs font-bold uppercase tracking-wider text-slate-500">
          Financial Analyst
        </p>
        <div className="mt-1 flex flex-wrap items-end justify-between gap-3">
          <h2 className="text-3xl font-semibold">CMA Workbench</h2>
          <div className="flex flex-wrap gap-2">
            <Button
              disabled={!active || createDraftMutation.isPending}
              onClick={() => createDraftMutation.mutate()}
            >
              <RefreshCw size={16} />
              {draft ? "Open Draft" : "New Draft"}
            </Button>
          </div>
        </div>
      </header>

      {error ? (
        <div className="rounded-md bg-[#ffe0d2] px-4 py-3 text-sm text-[#7d3b20]">
          {(error as Error).message}
        </div>
      ) : null}

      <div className="flex flex-wrap gap-2 border-b border-slate-200">
        <WorkbenchTabButton active={tab === "snapshots"} onClick={() => setTab("snapshots")}>
          Snapshots
        </WorkbenchTabButton>
        <WorkbenchTabButton active={tab === "assumptions"} onClick={() => setTab("assumptions")}>
          Assumptions
        </WorkbenchTabButton>
        <WorkbenchTabButton
          active={tab === "correlations"}
          onClick={() => setTab("correlations")}
        >
          Correlations
        </WorkbenchTabButton>
        <WorkbenchTabButton active={tab === "frontier"} onClick={() => setTab("frontier")}>
          Frontier
        </WorkbenchTabButton>
        <WorkbenchTabButton active={tab === "audit"} onClick={() => setTab("audit")}>
          Audit
        </WorkbenchTabButton>
      </div>

      {tab === "snapshots" ? (
        <SnapshotsTab
          active={active}
          draft={draft}
          isCreating={createDraftMutation.isPending}
          isPublishing={publishMutation.isPending}
          publishNote={publishNote}
          onCreateDraft={() => createDraftMutation.mutate()}
          onEditDraft={() => {
            if (draft) {
              setWorkingDraft(cloneSnapshot(draft));
              setTab("assumptions");
            }
          }}
          onPublish={() => workingDraft && publishMutation.mutate(workingDraft)}
          onPublishNoteChange={setPublishNote}
          publishDisabled={
            !workingDraft ||
            validationMessages.length > 0 ||
            !publishNote.trim() ||
            saveDraftMutation.isPending
          }
        />
      ) : null}

      {tab === "assumptions" ? (
        <AssumptionsTab
          snapshot={selectedSnapshot}
          validationMessages={validationMessages}
          isDraft={Boolean(workingDraft)}
          isSaving={saveDraftMutation.isPending}
          onSave={() => workingDraft && saveDraftMutation.mutate(workingDraft)}
          onUpdateFund={(fundId, field, value) =>
            setWorkingDraft((current) => updateFund(current, fundId, field, value))
          }
        />
      ) : null}

      {tab === "correlations" ? (
        <CorrelationsTab
          snapshot={selectedSnapshot}
          validationMessages={validationMessages}
          isDraft={Boolean(workingDraft)}
          isSaving={saveDraftMutation.isPending}
          onSave={() => workingDraft && saveDraftMutation.mutate(workingDraft)}
          onUpdateCorrelation={(rowId, colId, value) =>
            setWorkingDraft((current) => updateCorrelation(current, rowId, colId, value))
          }
        />
      ) : null}

      {tab === "frontier" ? (
        <FrontierTab
          frontier={frontier.data ?? null}
          isLoading={frontier.isLoading}
          hasUnsavedDraft={hasUnsavedDraft}
          validationMessages={validationMessages}
        />
      ) : null}

      {tab === "audit" ? <AuditTab events={audit.data ?? []} isLoading={audit.isLoading} /> : null}
    </div>
  );
}

function SnapshotsTab({
  active,
  draft,
  isCreating,
  isPublishing,
  publishDisabled,
  publishNote,
  onCreateDraft,
  onEditDraft,
  onPublish,
  onPublishNoteChange,
}: {
  active: CMASnapshot | null;
  draft: CMASnapshot | null;
  isCreating: boolean;
  isPublishing: boolean;
  publishDisabled: boolean;
  publishNote: string;
  onCreateDraft: () => void;
  onEditDraft: () => void;
  onPublish: () => void;
  onPublishNoteChange: (note: string) => void;
}) {
  return (
    <div className="grid grid-cols-[1.1fr_0.9fr] gap-5 max-xl:grid-cols-1">
      <WorkbenchPanel icon={<Database size={17} />} title="Active Snapshot">
        {active ? (
          <div className="space-y-4">
            <SnapshotHeader snapshot={active} statusLabel="Active" />
            {active.latest_publish_note ? (
              <div className="rounded-md bg-mist px-3 py-2 text-sm text-slate-700">
                {active.latest_publish_note}
              </div>
            ) : null}
            <FundTiles snapshot={active} />
          </div>
        ) : (
          <EmptyPanelText label="No active CMA snapshot" />
        )}
      </WorkbenchPanel>
      <WorkbenchPanel icon={<FileText size={17} />} title="Draft Snapshot">
        {draft ? (
          <div className="space-y-4">
            <SnapshotHeader snapshot={draft} statusLabel="Draft" />
            <div className="flex flex-wrap gap-2">
              <Button onClick={onEditDraft}>Edit Draft</Button>
            </div>
            <label className="block text-sm font-semibold text-slate-700">
              Publish note
              <textarea
                className="mt-2 min-h-24 w-full rounded-md border border-slate-200 px-3 py-2 font-normal outline-none focus:border-spruce"
                onChange={(event) => onPublishNoteChange(event.target.value)}
                value={publishNote}
              />
            </label>
            <Button disabled={publishDisabled || isPublishing} onClick={onPublish}>
              <CheckCircle2 size={16} />
              {isPublishing ? "Publishing" : "Publish"}
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            <EmptyPanelText label="No open draft" />
            <Button disabled={!active || isCreating} onClick={onCreateDraft}>
              <RefreshCw size={16} />
              {isCreating ? "Opening" : "New Draft"}
            </Button>
          </div>
        )}
      </WorkbenchPanel>
    </div>
  );
}

function AssumptionsTab({
  snapshot,
  validationMessages,
  isDraft,
  isSaving,
  onSave,
  onUpdateFund,
}: {
  snapshot: CMASnapshot | null;
  validationMessages: string[];
  isDraft: boolean;
  isSaving: boolean;
  onSave: () => void;
  onUpdateFund: (
    fundId: string,
    field: "expected_return" | "volatility" | "optimizer_eligible",
    value: string | boolean,
  ) => void;
}) {
  if (!snapshot) {
    return <EmptyPanelText label="No CMA snapshot available" />;
  }
  return (
    <WorkbenchPanel icon={<Database size={17} />} title="Assumptions">
      <ValidationPanel messages={validationMessages} />
      <div className="overflow-x-auto">
        <table className="w-full min-w-[820px] text-left text-sm">
          <thead className="border-b border-slate-100 text-xs uppercase tracking-wider text-slate-500">
            <tr>
              <th className="py-2 pr-3">Fund</th>
              <th className="px-3 py-2">Expected Return</th>
              <th className="px-3 py-2">Volatility</th>
              <th className="px-3 py-2">Eligible</th>
              <th className="px-3 py-2">Whole Portfolio</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {snapshot.fund_assumptions.map((fund) => (
              <tr key={fund.fund_id}>
                <td className="py-2 pr-3 font-medium">{fund.name}</td>
                <td className="px-3 py-2">
                  <input
                    className="h-10 w-full rounded-md border border-slate-200 px-2 outline-none focus:border-spruce disabled:bg-slate-50"
                    disabled={!isDraft}
                    onChange={(event) =>
                      onUpdateFund(fund.fund_id, "expected_return", event.target.value)
                    }
                    step="0.0001"
                    type="number"
                    value={fund.expected_return}
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    className="h-10 w-full rounded-md border border-slate-200 px-2 outline-none focus:border-spruce disabled:bg-slate-50"
                    disabled={!isDraft}
                    onChange={(event) =>
                      onUpdateFund(fund.fund_id, "volatility", event.target.value)
                    }
                    step="0.0001"
                    type="number"
                    value={fund.volatility}
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    aria-label={`${fund.name} eligible`}
                    checked={fund.optimizer_eligible}
                    disabled={!isDraft}
                    onChange={(event) =>
                      onUpdateFund(fund.fund_id, "optimizer_eligible", event.target.checked)
                    }
                    type="checkbox"
                  />
                </td>
                <td className="px-3 py-2">{fund.is_whole_portfolio ? "Yes" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {isDraft ? (
        <div className="mt-4 flex justify-end">
          <Button disabled={isSaving || validationMessages.length > 0} onClick={onSave}>
            <Save size={16} />
            {isSaving ? "Saving" : "Save Draft"}
          </Button>
        </div>
      ) : null}
    </WorkbenchPanel>
  );
}

function CorrelationsTab({
  snapshot,
  validationMessages,
  isDraft,
  isSaving,
  onSave,
  onUpdateCorrelation,
}: {
  snapshot: CMASnapshot | null;
  validationMessages: string[];
  isDraft: boolean;
  isSaving: boolean;
  onSave: () => void;
  onUpdateCorrelation: (rowId: string, colId: string, value: string) => void;
}) {
  if (!snapshot) {
    return <EmptyPanelText label="No CMA snapshot available" />;
  }
  return (
    <WorkbenchPanel icon={<Database size={17} />} title="Correlations">
      <ValidationPanel messages={validationMessages} />
      <div className="overflow-x-auto">
        <table className="min-w-[980px] border-separate border-spacing-0 text-sm">
          <thead>
            <tr>
              <th className="sticky left-0 z-10 bg-white p-2 text-left text-xs uppercase tracking-wider text-slate-500">
                Fund
              </th>
              {snapshot.fund_assumptions.map((fund) => (
                <th
                  className="max-w-28 p-2 text-left text-xs uppercase tracking-wider text-slate-500"
                  key={fund.fund_id}
                >
                  {shortFundName(fund.name)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {snapshot.fund_assumptions.map((rowFund) => (
              <tr key={rowFund.fund_id}>
                <th className="sticky left-0 z-10 border-t border-slate-100 bg-white p-2 text-left font-medium">
                  {shortFundName(rowFund.name)}
                </th>
                {snapshot.fund_assumptions.map((colFund) => {
                  const diagonal = rowFund.fund_id === colFund.fund_id;
                  return (
                    <td className="border-t border-slate-100 p-1" key={colFund.fund_id}>
                      <input
                        aria-label={`${rowFund.name} to ${colFund.name} correlation`}
                        className="h-9 w-24 rounded-md border border-slate-200 px-2 text-right outline-none focus:border-spruce disabled:bg-slate-50"
                        disabled={!isDraft || diagonal}
                        onChange={(event) =>
                          onUpdateCorrelation(
                            rowFund.fund_id,
                            colFund.fund_id,
                            event.target.value,
                          )
                        }
                        step="0.01"
                        type="number"
                        value={correlationValue(snapshot, rowFund.fund_id, colFund.fund_id)}
                      />
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {isDraft ? (
        <div className="mt-4 flex justify-end">
          <Button disabled={isSaving || validationMessages.length > 0} onClick={onSave}>
            <Save size={16} />
            {isSaving ? "Saving" : "Save Draft"}
          </Button>
        </div>
      ) : null}
    </WorkbenchPanel>
  );
}

function FrontierTab({
  frontier,
  hasUnsavedDraft,
  isLoading,
  validationMessages,
}: {
  frontier: CmaFrontier | null;
  hasUnsavedDraft: boolean;
  isLoading: boolean;
  validationMessages: string[];
}) {
  return (
    <WorkbenchPanel icon={<BarChart3 size={17} />} title="Efficient Frontier">
      <ValidationPanel messages={validationMessages} />
      {validationMessages.length ? null : isLoading ? (
        <EmptyPanelText label="Loading frontier" />
      ) : frontier ? (
        <div className="space-y-4">
          {hasUnsavedDraft ? (
            <div className="rounded-md bg-[#fff1c7] px-3 py-2 text-sm text-[#775b0b]">
              Save the draft to refresh the frontier preview.
            </div>
          ) : null}
          <div className="text-sm text-slate-600">
            {frontier.efficient.length} efficient points · {frontier.fund_points.length} funds
          </div>
          <FrontierChart frontier={frontier} />
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="border-b border-slate-100 text-xs uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="py-2 pr-3">Fund</th>
                  <th className="px-3 py-2">Return</th>
                  <th className="px-3 py-2">Volatility</th>
                  <th className="px-3 py-2">Eligible</th>
                  <th className="px-3 py-2">Whole Portfolio</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {frontier.fund_points.map((fund) => (
                  <tr key={fund.id}>
                    <td className="py-2 pr-3 font-medium">{fund.name}</td>
                    <td className="px-3 py-2">{percent.format(fund.expected_return)}</td>
                    <td className="px-3 py-2">{percent.format(fund.volatility)}</td>
                    <td className="px-3 py-2">{fund.optimizer_eligible ? "Yes" : "No"}</td>
                    <td className="px-3 py-2">{fund.is_whole_portfolio ? "Yes" : "No"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <EmptyPanelText label="Frontier unavailable" />
      )}
    </WorkbenchPanel>
  );
}

function FrontierChart({ frontier }: { frontier: CmaFrontier }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  useEffect(() => {
    if (!canvasRef.current) {
      return;
    }
    const eligibleFunds = frontier.fund_points.filter((fund) => fund.optimizer_eligible);
    const ineligibleFunds = frontier.fund_points.filter((fund) => !fund.optimizer_eligible);
    const chart = new Chart(canvasRef.current, {
      type: "scatter",
      data: {
        datasets: [
          {
            type: "line",
            label: "Efficient Frontier",
            data: frontier.efficient.map((point) => ({
              x: point.volatility * 100,
              y: point.expected_return * 100,
            })),
            borderColor: "#1f6b5d",
            backgroundColor: "#1f6b5d",
            borderWidth: 2,
            pointRadius: 2.5,
            tension: 0.25,
          },
          {
            type: "scatter",
            label: "Eligible Funds",
            data: eligibleFunds.map((fund) => ({
              x: fund.volatility * 100,
              y: fund.expected_return * 100,
            })),
            backgroundColor: "#b56b45",
            pointRadius: 5,
            pointStyle: "circle",
          },
          {
            type: "scatter",
            label: "Ineligible Funds",
            data: ineligibleFunds.map((fund) => ({
              x: fund.volatility * 100,
              y: fund.expected_return * 100,
            })),
            backgroundColor: "#94a3b8",
            pointRadius: 5,
            pointStyle: "rectRot",
          },
        ],
      },
      options: {
        animation: false,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "bottom" },
          tooltip: {
            callbacks: {
              label(context) {
                const x = Number(context.parsed.x).toFixed(2);
                const y = Number(context.parsed.y).toFixed(2);
                return `${context.dataset.label}: return ${y}%, vol ${x}%`;
              },
            },
          },
        },
        scales: {
          x: {
            title: { display: true, text: "Volatility" },
            ticks: { callback: (value) => `${value}%` },
          },
          y: {
            title: { display: true, text: "Expected Return" },
            ticks: { callback: (value) => `${value}%` },
          },
        },
      },
    });
    return () => chart.destroy();
  }, [frontier]);
  return (
    <div className="h-[360px] rounded-md border border-slate-100 bg-white p-3">
      <canvas aria-label="Efficient frontier chart" ref={canvasRef} role="img" />
    </div>
  );
}

function AuditTab({ events, isLoading }: { events: CmaAuditEvent[]; isLoading: boolean }) {
  return (
    <WorkbenchPanel icon={<History size={17} />} title="Audit">
      {isLoading ? (
        <EmptyPanelText label="Loading audit events" />
      ) : events.length ? (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead className="border-b border-slate-100 text-xs uppercase tracking-wider text-slate-500">
              <tr>
                <th className="py-2 pr-3">When</th>
                <th className="px-3 py-2">Actor</th>
                <th className="px-3 py-2">Action</th>
                <th className="px-3 py-2">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {events.map((event) => (
                <tr key={event.id}>
                  <td className="py-2 pr-3">{new Date(event.created_at).toLocaleString()}</td>
                  <td className="px-3 py-2">{event.actor}</td>
                  <td className="px-3 py-2">{event.action.replace(/_/g, " ")}</td>
                  <td className="px-3 py-2 text-slate-600">{auditSummary(event)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyPanelText label="No CMA audit events" />
      )}
    </WorkbenchPanel>
  );
}

function WorkbenchPanel({
  children,
  icon,
  title,
}: {
  children: ReactNode;
  icon: ReactNode;
  title: string;
}) {
  return (
    <section className="rounded-md border border-slate-200 bg-white shadow-soft">
      <div className="flex items-center gap-2 border-b border-slate-100 px-4 py-3">
        <span className="text-spruce">{icon}</span>
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">{title}</h3>
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

function WorkbenchTabButton({
  active,
  children,
  onClick,
}: {
  active: boolean;
  children: ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      className={`border-b-2 px-3 py-2 text-sm font-semibold ${
        active
          ? "border-spruce text-ink"
          : "border-transparent text-slate-500 hover:border-slate-300"
      }`}
      onClick={onClick}
      type="button"
    >
      {children}
    </button>
  );
}

function SnapshotHeader({
  snapshot,
  statusLabel,
}: {
  snapshot: CMASnapshot;
  statusLabel: string;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <div className="text-lg font-semibold">{snapshot.name}</div>
        <div className="mt-1 text-sm text-slate-500">
          Version {snapshot.version} · {snapshot.source}
        </div>
        {snapshot.published_at ? (
          <div className="mt-1 text-xs text-slate-500">
            Published {new Date(snapshot.published_at).toLocaleString()}
          </div>
        ) : null}
      </div>
      <span className="rounded-full bg-mist px-2 py-1 text-xs font-bold uppercase">
        {statusLabel}
      </span>
    </div>
  );
}

function FundTiles({ snapshot }: { snapshot: CMASnapshot }) {
  return (
    <div className="grid grid-cols-4 gap-2 max-lg:grid-cols-2 max-sm:grid-cols-1">
      {snapshot.fund_assumptions.map((fund) => (
        <div className="rounded-md bg-[#fbfaf5] px-3 py-2 text-sm" key={fund.fund_id}>
          <div className="font-medium">{fund.name}</div>
          <div className="text-xs text-slate-500">
            Return {percent.format(Number(fund.expected_return))} · Vol{" "}
            {percent.format(Number(fund.volatility))}
          </div>
        </div>
      ))}
    </div>
  );
}

function ValidationPanel({ messages }: { messages: string[] }) {
  if (!messages.length) {
    return null;
  }
  return (
    <div className="mb-4 rounded-md bg-[#ffe0d2] px-3 py-2 text-sm text-[#7d3b20]">
      {messages.map((message) => (
        <div key={message}>{message}</div>
      ))}
    </div>
  );
}

function EmptyPanelText({ label }: { label: string }) {
  return <div className="rounded-md bg-mist px-4 py-5 text-sm text-slate-600">{label}</div>;
}

function cloneSnapshot(snapshot: CMASnapshot): CMASnapshot {
  return JSON.parse(JSON.stringify(snapshot)) as CMASnapshot;
}

function updateFund(
  snapshot: CMASnapshot | null,
  fundId: string,
  field: "expected_return" | "volatility" | "optimizer_eligible",
  value: string | boolean,
): CMASnapshot | null {
  if (!snapshot) {
    return snapshot;
  }
  return {
    ...snapshot,
    fund_assumptions: snapshot.fund_assumptions.map((fund) =>
      fund.fund_id === fundId ? { ...fund, [field]: value } : fund,
    ),
  };
}

function updateCorrelation(
  snapshot: CMASnapshot | null,
  rowId: string,
  colId: string,
  value: string,
): CMASnapshot | null {
  if (!snapshot) {
    return snapshot;
  }
  return {
    ...snapshot,
    correlations: snapshot.correlations.map((cell) => {
      if (
        (cell.row_fund_id === rowId && cell.col_fund_id === colId) ||
        (cell.row_fund_id === colId && cell.col_fund_id === rowId)
      ) {
        return { ...cell, correlation: value };
      }
      return cell;
    }),
  };
}

function correlationValue(snapshot: CMASnapshot, rowId: string, colId: string): string {
  return (
    snapshot.correlations.find(
      (cell) => cell.row_fund_id === rowId && cell.col_fund_id === colId,
    )?.correlation ?? ""
  );
}

function validateDraft(snapshot: CMASnapshot): string[] {
  const messages: string[] = [];
  const eligibleCount = snapshot.fund_assumptions.filter((fund) => fund.optimizer_eligible).length;
  if (eligibleCount < 2) {
    messages.push("At least two funds must remain optimizer eligible.");
  }
  for (const fund of snapshot.fund_assumptions) {
    const expectedReturn = Number(fund.expected_return);
    const volatility = Number(fund.volatility);
    if (!Number.isFinite(expectedReturn) || expectedReturn <= -1 || expectedReturn >= 1) {
      messages.push(`${fund.name} expected return must be between -100% and 100%.`);
    }
    if (!Number.isFinite(volatility) || volatility <= 0 || volatility >= 2) {
      messages.push(`${fund.name} volatility must be between 0% and 200%.`);
    }
  }
  const fundIds = snapshot.fund_assumptions.map((fund) => fund.fund_id);
  const correlationMap = new Map(
    snapshot.correlations.map((cell) => [
      `${cell.row_fund_id}:${cell.col_fund_id}`,
      Number(cell.correlation),
    ]),
  );
  for (const rowId of fundIds) {
    for (const colId of fundIds) {
      const value = correlationMap.get(`${rowId}:${colId}`);
      const inverse = correlationMap.get(`${colId}:${rowId}`);
      if (value === undefined || !Number.isFinite(value)) {
        messages.push("Every correlation matrix cell must be numeric.");
        return uniqueMessages(messages);
      }
      if (value < -1 || value > 1) {
        messages.push("Correlation values must be between -1 and 1.");
      }
      if (rowId === colId && Math.abs(value - 1) > 0.00001) {
        messages.push("Correlation diagonal values must be 1.");
      }
      if (inverse !== undefined && Number.isFinite(inverse) && Math.abs(value - inverse) > 0.00001) {
        messages.push("Correlation matrix must be symmetric.");
      }
    }
  }
  return uniqueMessages(messages);
}

function uniqueMessages(messages: string[]): string[] {
  return [...new Set(messages)];
}

function shortFundName(name: string): string {
  return name.replace("SH ", "").replace("Global Small-Cap Eq", "Global SC");
}

function auditSummary(event: CmaAuditEvent): string {
  const metadata = event.metadata;
  const publishNote = typeof metadata.publish_note === "string" ? metadata.publish_note : "";
  if (publishNote) {
    return publishNote;
  }
  const fundDiffs = Array.isArray(metadata.fund_diffs) ? metadata.fund_diffs.length : 0;
  const pairDiffs =
    typeof metadata.correlation_pair_diff_count === "number"
      ? metadata.correlation_pair_diff_count
      : 0;
  const pieces = [];
  if (typeof metadata.version === "number") {
    pieces.push(`v${metadata.version}`);
  }
  if (fundDiffs) {
    pieces.push(`${fundDiffs} fund change${fundDiffs === 1 ? "" : "s"}`);
  }
  if (pairDiffs) {
    pieces.push(`${pairDiffs} correlation pair${pairDiffs === 1 ? "" : "s"}`);
  }
  if (typeof metadata.snapshot_hash === "string") {
    pieces.push(`hash ${metadata.snapshot_hash.slice(0, 12)}`);
  }
  return pieces.join(" · ") || "Recorded";
}
