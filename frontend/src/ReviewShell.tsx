import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  FileText,
  Link2,
  Plus,
  RefreshCw,
  ShieldCheck,
  Upload,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  approveReviewSection,
  commitReviewWorkspace,
  createReviewWorkspace,
  fetchClients,
  fetchReviewFacts,
  fetchReviewMatches,
  fetchReviewWorkspace,
  fetchReviewWorkspaces,
  manualReconcileReviewWorkspace,
  patchReviewState,
  retryReviewDocument,
  uploadReviewDocuments,
} from "./api";
import { Button } from "./components/ui/button";
import type {
  ExtractedFact,
  HouseholdSummary,
  MatchCandidate,
  Readiness,
  ReviewDocument,
  ReviewedClientState,
  ReviewWorkspace,
  ReviewWorkspaceSummary,
} from "./types";

const currency = new Intl.NumberFormat("en-CA", {
  style: "currency",
  currency: "CAD",
  maximumFractionDigits: 0,
});

const requiredSections = ["household", "people", "accounts", "goals", "goal_account_mapping", "risk"];

type ApprovalStatus =
  | "approved"
  | "approved_with_unknowns"
  | "needs_attention"
  | "not_ready_for_recommendation";

type ReviewShellProps = {
  onOpenClient: (id: string) => void;
};

export function ReviewShell({ onOpenClient }: ReviewShellProps) {
  const queryClient = useQueryClient();
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string>("");
  const workspaces = useQuery({
    queryKey: ["review-workspaces"],
    queryFn: fetchReviewWorkspaces,
    refetchInterval: 3500,
  });
  const clients = useQuery({
    queryKey: ["clients"],
    queryFn: fetchClients,
  });
  const workspace = useQuery({
    queryKey: ["review-workspace", selectedWorkspaceId],
    queryFn: () => fetchReviewWorkspace(selectedWorkspaceId),
    enabled: Boolean(selectedWorkspaceId),
    refetchInterval: 3000,
  });
  const facts = useQuery({
    queryKey: ["review-facts", selectedWorkspaceId],
    queryFn: () => fetchReviewFacts(selectedWorkspaceId),
    enabled: Boolean(selectedWorkspaceId),
    refetchInterval: 5000,
  });

  useEffect(() => {
    if (!selectedWorkspaceId && workspaces.data?.length) {
      setSelectedWorkspaceId(workspaces.data[0].external_id);
    }
  }, [selectedWorkspaceId, workspaces.data]);

  const currentWorkspace = workspace.data;

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Review Intake</p>
          <h2 className="mt-1 text-3xl font-semibold">Secure Client Review</h2>
          <p className="mt-2 max-w-3xl text-sm text-slate-600">
            Steadyhand IS intake, review, and engine-readiness workspace.
          </p>
        </div>
        <Button
          disabled={workspaces.isFetching || workspace.isFetching}
          onClick={() => {
            void workspaces.refetch();
            void workspace.refetch();
            void facts.refetch();
          }}
          variant="secondary"
        >
          <RefreshCw size={16} className={workspaces.isFetching ? "animate-spin" : ""} />
          Refresh
        </Button>
      </header>

      <div className="grid grid-cols-[310px_1fr] gap-5 max-xl:grid-cols-1">
        <div className="space-y-5">
          <WorkspaceCreator
            onCreated={(id) => {
              setSelectedWorkspaceId(id);
              void queryClient.invalidateQueries({ queryKey: ["review-workspaces"] });
            }}
          />
          <WorkspaceList
            selectedWorkspaceId={selectedWorkspaceId}
            workspaces={workspaces.data ?? []}
            onSelect={setSelectedWorkspaceId}
          />
        </div>

        {currentWorkspace ? (
          <WorkspaceReview
            clients={clients.data ?? []}
            facts={facts.data ?? []}
            onOpenClient={onOpenClient}
            workspace={currentWorkspace}
          />
        ) : (
          <section className="rounded-md border border-slate-200 bg-white p-6 shadow-soft">
            <PanelTitle icon={<FileText size={17} />} title="Workspace" />
            <div className="mt-5 rounded-md bg-mist px-4 py-5 text-sm text-slate-600">
              Create or select a review workspace.
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

function WorkspaceCreator({ onCreated }: { onCreated: (id: string) => void }) {
  const [label, setLabel] = useState("");
  const [dataOrigin, setDataOrigin] = useState("real_derived");
  const mutation = useMutation({
    mutationFn: () => createReviewWorkspace(label.trim(), dataOrigin),
    onSuccess: (workspace) => {
      setLabel("");
      onCreated(workspace.external_id);
    },
  });

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4 shadow-soft">
      <div className="mb-3 flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-slate-500">
        <Plus size={16} className="text-spruce" />
        New Review
      </div>
      <form
        className="space-y-3"
        onSubmit={(event) => {
          event.preventDefault();
          if (label.trim()) {
            mutation.mutate();
          }
        }}
      >
        <input
          className="min-h-10 w-full rounded-md border border-slate-200 px-3 text-sm outline-none focus:border-spruce"
          onChange={(event) => setLabel(event.target.value)}
          placeholder="Household or bundle label"
          value={label}
        />
        <select
          className="min-h-10 w-full rounded-md border border-slate-200 px-3 text-sm outline-none focus:border-spruce"
          onChange={(event) => setDataOrigin(event.target.value)}
          value={dataOrigin}
        >
          <option value="real_derived">Real-derived review</option>
          <option value="synthetic">Synthetic test review</option>
        </select>
        <Button className="w-full" disabled={!label.trim() || mutation.isPending} type="submit">
          <Plus size={16} />
          {mutation.isPending ? "Creating" : "Create Workspace"}
        </Button>
        {mutation.error ? <ErrorLine message={mutation.error.message} /> : null}
      </form>
    </section>
  );
}

function WorkspaceList({
  workspaces,
  selectedWorkspaceId,
  onSelect,
}: {
  workspaces: ReviewWorkspaceSummary[];
  selectedWorkspaceId: string;
  onSelect: (id: string) => void;
}) {
  return (
    <section className="rounded-md border border-slate-200 bg-white p-4 shadow-soft">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">Workspaces</h3>
        <FileText size={16} className="text-slate-400" />
      </div>
      <div className="space-y-2">
        {workspaces.length ? (
          workspaces.map((workspace) => (
            <button
              className={`w-full rounded-md border px-3 py-3 text-left transition ${
                selectedWorkspaceId === workspace.external_id
                  ? "border-spruce bg-mist"
                  : "border-slate-200 hover:border-slate-300"
              }`}
              key={workspace.external_id}
              onClick={() => onSelect(workspace.external_id)}
              type="button"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold">{workspace.label}</div>
                  <div className="mt-1 text-xs text-slate-500">{workspace.document_count} documents</div>
                </div>
                <StatusBadge status={workspace.status} />
              </div>
            </button>
          ))
        ) : (
          <div className="rounded-md bg-mist px-3 py-3 text-sm text-slate-600">No workspaces</div>
        )}
      </div>
    </section>
  );
}

function WorkspaceReview({
  workspace,
  facts,
  clients,
  onOpenClient,
}: {
  workspace: ReviewWorkspace;
  facts: ExtractedFact[];
  clients: HouseholdSummary[];
  onOpenClient: (id: string) => void;
}) {
  const queryClient = useQueryClient();
  const state = normalizeState(workspace.reviewed_state);
  const readiness = normalizeReadiness(workspace.readiness, state.readiness);
  const matchesMutation = useMutation({
    mutationFn: () => fetchReviewMatches(workspace.external_id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["review-workspace", workspace.external_id] });
    },
  });
  const matches = matchesMutation.data?.candidates ?? workspace.match_candidates ?? [];

  const invalidateWorkspace = () => {
    void queryClient.invalidateQueries({ queryKey: ["review-workspace", workspace.external_id] });
    void queryClient.invalidateQueries({ queryKey: ["review-workspaces"] });
    void queryClient.invalidateQueries({ queryKey: ["review-facts", workspace.external_id] });
  };

  return (
    <div className="min-w-0 space-y-5">
      <div className="grid grid-cols-5 gap-3 max-xl:grid-cols-2 max-sm:grid-cols-1">
        <Metric label="Status" value={humanize(workspace.status)} />
        <Metric label="Documents" value={String(workspace.documents.length)} />
        <Metric label="Facts" value={String(facts.length)} />
        <Metric label="Engine Ready" value={readiness.engine_ready ? "Yes" : "No"} />
        <Metric label="Construction" value={readiness.construction_ready ? "Yes" : "No"} />
      </div>

      <div className="grid grid-cols-[0.9fr_1.1fr] gap-5 max-2xl:grid-cols-1">
        <div className="space-y-5">
          <UploadPanel workspace={workspace} onChanged={invalidateWorkspace} />
          <DocumentPanel documents={workspace.documents} onChanged={invalidateWorkspace} workspaceId={workspace.external_id} />
          <JobPanel jobs={workspace.processing_jobs} workerHealth={workspace.worker_health} />
          <FactPanel facts={facts} />
          <TimelinePanel events={workspace.timeline} />
        </div>
        <div className="space-y-5">
          <ReadinessPanel readiness={readiness} />
          <AdvisorReviewPanel facts={facts} state={state} workspaceId={workspace.external_id} />
          <SectionApprovalPanel
            readiness={readiness}
            state={state}
            workspace={workspace}
            onChanged={invalidateWorkspace}
          />
          <StateSummary state={state} />
          <MatchCommitPanel
            clients={clients}
            matches={matches}
            matchesError={matchesMutation.error?.message}
            onFindMatches={() => matchesMutation.mutate()}
            onOpenClient={onOpenClient}
            readiness={readiness}
            workspace={workspace}
          />
        </div>
      </div>
    </div>
  );
}

function UploadPanel({ workspace, onChanged }: { workspace: ReviewWorkspace; onChanged: () => void }) {
  const [files, setFiles] = useState<FileList | null>(null);
  const mutation = useMutation({
    mutationFn: () => {
      if (!files) {
        throw new Error("Select files first.");
      }
      return uploadReviewDocuments(workspace.external_id, files);
    },
    onSuccess: () => {
      setFiles(null);
      onChanged();
    },
  });

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4 shadow-soft">
      <PanelTitle icon={<Upload size={17} />} title="Upload Bundle" />
      <div className="mt-4 space-y-3">
        <input
          accept=".pdf,.docx,.xlsx,.csv,.txt,.md,.png,.jpg,.jpeg,.tif,.tiff"
          className="block w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
          multiple
          onChange={(event) => setFiles(event.target.files)}
          type="file"
        />
        <Button disabled={!files || mutation.isPending} onClick={() => mutation.mutate()}>
          <Upload size={16} />
          {mutation.isPending ? "Uploading" : "Upload Files"}
        </Button>
        {mutation.data ? (
          <div className="rounded-md bg-mist px-3 py-2 text-sm text-slate-700">
            Uploaded {mutation.data.uploaded.length}; duplicates {mutation.data.duplicates.length}
            {mutation.data.ignored?.length ? `; ignored ${mutation.data.ignored.length} system file(s)` : ""}.
          </div>
        ) : null}
        {mutation.error ? <ErrorLine message={mutation.error.message} /> : null}
      </div>
    </section>
  );
}

function DocumentPanel({
  documents,
  workspaceId,
  onChanged,
}: {
  documents: ReviewDocument[];
  workspaceId: string;
  onChanged: () => void;
}) {
  const retryMutation = useMutation({
    mutationFn: (documentId: number) => retryReviewDocument(workspaceId, documentId),
    onSuccess: onChanged,
  });

  return (
    <section className="rounded-md border border-slate-200 bg-white shadow-soft">
      <PanelTitle icon={<FileText size={17} />} title="Documents" />
      <div className="divide-y divide-slate-100">
        {documents.length ? (
          documents.map((document) => (
            <div className="grid grid-cols-[1fr_auto] items-center gap-3 px-4 py-3" key={document.id}>
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold">{document.original_filename}</div>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                  <span>{document.document_type}</span>
                  <span>{formatBytes(document.file_size)}</span>
                  {document.failure_reason ? <span>{document.failure_reason}</span> : null}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <StatusBadge status={document.status} />
                {["failed", "unsupported"].includes(document.status) ? (
                  <Button
                    disabled={retryMutation.isPending}
                    onClick={() => retryMutation.mutate(document.id)}
                    variant="secondary"
                  >
                    <RefreshCw size={15} />
                    Retry
                  </Button>
                ) : null}
              </div>
            </div>
          ))
        ) : (
          <div className="px-4 py-4 text-sm text-slate-600">No documents uploaded.</div>
        )}
      </div>
      {retryMutation.error ? <div className="px-4 pb-4"><ErrorLine message={retryMutation.error.message} /></div> : null}
    </section>
  );
}

function JobPanel({
  jobs,
  workerHealth,
}: {
  jobs: ReviewWorkspace["processing_jobs"];
  workerHealth: ReviewWorkspace["worker_health"];
}) {
  const activeJobs = jobs.filter((job) => ["queued", "processing"].includes(job.status));
  return (
    <section className="rounded-md border border-slate-200 bg-white shadow-soft">
      <PanelTitle icon={<RefreshCw size={17} />} title="Worker Queue" />
      <div className="border-b border-slate-100 px-4 py-3 text-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="font-semibold">Worker health</span>
          <StatusBadge status={workerHealth?.status ?? "unknown"} />
        </div>
        <div className="mt-1 text-xs text-slate-500">
          {workerHealth?.last_seen_at ? `Last seen ${new Date(workerHealth.last_seen_at).toLocaleString()}` : "No worker heartbeat yet."}
        </div>
      </div>
      <div className="divide-y divide-slate-100">
        {activeJobs.length ? (
          activeJobs.map((job) => (
            <div className="grid grid-cols-[1fr_auto] gap-3 px-4 py-3 text-sm" key={job.id}>
              <div>
                <div className="font-semibold">{humanize(job.job_type)}</div>
                <div className="mt-1 text-xs text-slate-500">
                  Attempt {job.attempts}/{job.max_attempts}
                  {job.is_stale ? " · stale" : ""}
                </div>
              </div>
              <StatusBadge status={job.status} />
            </div>
          ))
        ) : (
          <div className="px-4 py-4 text-sm text-slate-600">No active jobs.</div>
        )}
      </div>
    </section>
  );
}

function FactPanel({ facts }: { facts: ExtractedFact[] }) {
  return (
    <section className="rounded-md border border-slate-200 bg-white shadow-soft">
      <PanelTitle icon={<ShieldCheck size={17} />} title="Extracted Facts" />
      <div className="max-h-[390px] divide-y divide-slate-100 overflow-auto">
        {facts.length ? (
          facts.map((fact) => (
            <div className="px-4 py-3 text-sm" key={fact.id}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-semibold">{fact.field_label || labelForField(fact.field)}</span>
                <span className="rounded-full bg-mist px-2 py-1 text-xs font-semibold uppercase text-slate-600">
                  {fact.confidence}
                </span>
              </div>
              <div className="mt-2 break-words rounded-md bg-[#fbfaf5] px-3 py-2 text-xs text-slate-700">
                {fact.evidence_quote || JSON.stringify(fact.value)}
              </div>
              <div className="mt-2 text-xs text-slate-500">
                {fact.document_name} {fact.source_location ? `- ${fact.source_location}` : ""}
                {fact.field ? ` · ${fact.field}` : ""}
              </div>
            </div>
          ))
        ) : (
          <div className="px-4 py-4 text-sm text-slate-600">No facts yet.</div>
        )}
      </div>
    </section>
  );
}

function TimelinePanel({ events }: { events: ReviewWorkspace["timeline"] }) {
  return (
    <section className="rounded-md border border-slate-200 bg-white shadow-soft">
      <PanelTitle icon={<FileText size={17} />} title="Workspace Timeline" />
      <div className="max-h-[260px] divide-y divide-slate-100 overflow-auto">
        {events?.length ? (
          events.map((event) => (
            <div className="px-4 py-3 text-sm" key={event.id}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-semibold">{humanize(event.action)}</span>
                <span className="text-xs text-slate-500">{new Date(event.created_at).toLocaleString()}</span>
              </div>
              <div className="mt-1 text-xs text-slate-500">
                {Object.entries(event.metadata ?? {})
                  .slice(0, 5)
                  .map(([key, value]) => `${humanize(key)}: ${String(value)}`)
                  .join(" · ")}
              </div>
            </div>
          ))
        ) : (
          <div className="px-4 py-4 text-sm text-slate-600">No sanitized activity yet.</div>
        )}
      </div>
    </section>
  );
}

function ReadinessPanel({ readiness }: { readiness: Readiness }) {
  return (
    <section className="rounded-md border border-slate-200 bg-white p-4 shadow-soft">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-slate-500">
          {readiness.engine_ready ? (
            <CheckCircle2 size={17} className="text-spruce" />
          ) : (
            <AlertTriangle size={17} className="text-copper" />
          )}
          Readiness
        </div>
        <StatusBadge
          status={readiness.engine_ready && readiness.construction_ready ? "engine_ready" : "needs_review"}
        />
      </div>
      <div className="mt-4 grid grid-cols-3 gap-3 max-sm:grid-cols-1">
        <div className="rounded-md bg-mist px-3 py-3">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-500">Engine</div>
          <div className="mt-1 text-lg font-semibold">{readiness.engine_ready ? "Ready" : "Incomplete"}</div>
        </div>
        <div className="rounded-md bg-mist px-3 py-3">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-500">Construction</div>
          <div className="mt-1 text-lg font-semibold">
            {readiness.construction_ready ? "Ready" : "Incomplete"}
          </div>
        </div>
        <div className="rounded-md bg-mist px-3 py-3">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-500">KYC</div>
          <div className="mt-1 text-lg font-semibold">
            {readiness.kyc_compliance_ready ? "Ready" : "Separate Review"}
          </div>
        </div>
      </div>
      {[...readiness.missing, ...readiness.construction_missing].length ? (
        <div className="mt-4 space-y-2">
          {[...readiness.missing, ...readiness.construction_missing].map((item) => (
            <div className="rounded-md border border-slate-200 px-3 py-2 text-sm" key={`${item.section}-${item.label}`}>
              <span className="font-semibold">{humanize(item.section)}</span>: {item.label}
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function AdvisorReviewPanel({
  workspaceId,
  state,
  facts,
}: {
  workspaceId: string;
  state: ReviewedClientState;
  facts: ExtractedFact[];
}) {
  const queryClient = useQueryClient();
  const [activeSection, setActiveSection] = useState("household");
  const [newMemberName, setNewMemberName] = useState("");
  const [newAccountType, setNewAccountType] = useState("RRSP");
  const [newGoalName, setNewGoalName] = useState("Retirement");
  const [newValue, setNewValue] = useState("");
  const mutation = useMutation({
    mutationFn: (payload: { patch: Partial<ReviewedClientState>; reason?: string; requires_reason?: boolean }) =>
      patchReviewState(workspaceId, payload.patch, {
        reason: payload.reason,
        requires_reason: payload.requires_reason,
      }),
    onSuccess: (payload) => {
      queryClient.setQueryData<ReviewWorkspace>(["review-workspace", workspaceId], (current) =>
        current
          ? { ...current, reviewed_state: payload.state, readiness: payload.readiness }
          : current,
      );
      void queryClient.invalidateQueries({ queryKey: ["review-workspace", workspaceId] });
      void queryClient.invalidateQueries({ queryKey: ["review-workspaces"] });
    },
  });
  const reconcileMutation = useMutation({
    mutationFn: () => manualReconcileReviewWorkspace(workspaceId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["review-workspace", workspaceId] });
      void queryClient.invalidateQueries({ queryKey: ["review-workspaces"] });
    },
  });

  const save = (patch: Partial<ReviewedClientState>, reason?: string, requiresReason = false) => {
    mutation.mutate({ patch, reason, requires_reason: requiresReason });
  };
  const sources = sourceMap(state);

  return (
    <section className="rounded-md border border-slate-200 bg-white shadow-soft">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-4 py-3">
        <PanelTitle icon={<ShieldCheck size={17} />} title="Advisor Review" />
        <Button disabled={reconcileMutation.isPending} onClick={() => reconcileMutation.mutate()} variant="secondary">
          <RefreshCw size={16} className={reconcileMutation.isPending ? "animate-spin" : ""} />
          Reconcile
        </Button>
      </div>
      <div className="flex flex-wrap gap-2 px-4 py-3">
        {requiredSections.map((section) => (
          <button
            className={`rounded-md border px-3 py-2 text-sm font-semibold ${
              activeSection === section ? "border-spruce bg-mist" : "border-slate-200 text-slate-600"
            }`}
            key={section}
            onClick={() => setActiveSection(section)}
            type="button"
          >
            {humanize(section)}
          </button>
        ))}
      </div>

      <div className="space-y-4 p-4">
        {activeSection === "household" ? (
          <div className="grid grid-cols-3 gap-3 max-lg:grid-cols-1">
            <ReviewInput
              label="Household name"
              value={stringValue(state.household.display_name)}
              source={sources.get("household.display_name")}
              onSave={(value, reason) =>
                save({ household: { ...state.household, display_name: value } }, reason, true)
              }
            />
            <ReviewInput
              label="Household type"
              value={stringValue(state.household.household_type, "couple")}
              source={sources.get("household.household_type")}
              onSave={(value, reason) =>
                save({ household: { ...state.household, household_type: value } }, reason, true)
              }
            />
            <ReviewInput
              label="Risk score"
              type="number"
              min={1}
              max={5}
              value={String(numberValue(state.risk.household_score ?? state.household.household_risk_score, 3))}
              source={sources.get("risk.household_score")}
              onSave={(value, reason) =>
                save(
                  {
                    household: { ...state.household, household_risk_score: Number(value) || 3 },
                    risk: { ...state.risk, household_score: Number(value) || 3 },
                  },
                  reason,
                  true,
                )
              }
            />
          </div>
        ) : null}

        {activeSection === "people" ? (
          <div className="space-y-3">
            {state.people.map((person, index) => (
              <div className="grid grid-cols-[1fr_120px_auto] gap-2 max-md:grid-cols-1" key={stringValue(person.id, `person-${index}`)}>
                <ReviewInput
                  label="Member name"
                  value={stringValue(person.name)}
                  source={sources.get(`people[${index}].display_name`) ?? sources.get(`people[${index}].name`)}
                  onSave={(value, reason) => {
                    const people = replaceAt(state.people, index, { ...person, name: value });
                    save({ people }, reason, true);
                  }}
                />
                <ReviewInput
                  label="Age"
                  type="number"
                  value={String(numberValue(person.age, 0))}
                  source={sources.get(`people[${index}].age`)}
                  onSave={(value, reason) => {
                    const people = replaceAt(state.people, index, { ...person, age: Number(value) || "" });
                    save({ people }, reason, true);
                  }}
                />
                <Button onClick={() => save({ people: removeAt(state.people, index) }, "advisor deleted member", true)} variant="secondary">
                  Delete
                </Button>
              </div>
            ))}
            <div className="grid grid-cols-[1fr_auto] gap-2 max-md:grid-cols-1">
              <input
                className="min-h-10 rounded-md border border-slate-200 px-3 text-sm"
                onChange={(event) => setNewMemberName(event.target.value)}
                placeholder="Add member"
                value={newMemberName}
              />
              <Button
                disabled={!newMemberName.trim()}
                onClick={() => {
                  save({ people: [...state.people, { id: safeId("person", newMemberName), name: newMemberName.trim(), age: 62 }] });
                  setNewMemberName("");
                }}
                variant="secondary"
              >
                <Plus size={16} />
                Member
              </Button>
            </div>
          </div>
        ) : null}

        {activeSection === "accounts" ? (
          <div className="space-y-3">
            {state.accounts.map((account, index) => (
              <div className="rounded-md border border-slate-100 p-3" key={stringValue(account.id, `account-${index}`)}>
                <div className="grid grid-cols-[1fr_160px_auto] gap-2 max-md:grid-cols-1">
                  <ReviewInput
                    label="Account type"
                    value={stringValue(account.type)}
                    source={sources.get(`accounts[${index}].account_type`) ?? sources.get(`accounts[${index}].type`)}
                    onSave={(value, reason) => save({ accounts: replaceAt(state.accounts, index, { ...account, type: value }) }, reason, true)}
                  />
                  <ReviewInput
                    label="Current value"
                    type="number"
                    value={String(numberValue(account.current_value, 0))}
                    source={sources.get(`accounts[${index}].current_value`) ?? sources.get(`accounts[${index}].account_value`)}
                    onSave={(value, reason) =>
                      save({ accounts: replaceAt(state.accounts, index, { ...account, current_value: Number(value) || 0 }) }, reason, true)
                    }
                  />
                  <Button onClick={() => save({ accounts: removeAt(state.accounts, index) }, "advisor deleted account", true)} variant="secondary">
                    Delete
                  </Button>
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
                  <StatusBadge status={account.missing_holdings_confirmed ? "approved_with_unknowns" : "needs_attention"} />
                  <Button
                    onClick={() =>
                      save({
                        accounts: replaceAt(state.accounts, index, {
                          ...account,
                          missing_holdings_confirmed: true,
                        }),
                      })
                    }
                    variant="secondary"
                  >
                    Confirm Missing Holdings
                  </Button>
                </div>
              </div>
            ))}
            <div className="grid grid-cols-[120px_1fr_auto] gap-2 max-md:grid-cols-1">
              <input className="min-h-10 rounded-md border border-slate-200 px-3 text-sm" onChange={(event) => setNewAccountType(event.target.value)} value={newAccountType} />
              <input className="min-h-10 rounded-md border border-slate-200 px-3 text-sm" onChange={(event) => setNewValue(event.target.value)} placeholder="Account value" type="number" value={newValue} />
              <Button
                disabled={!newValue.trim()}
                onClick={() => {
                  const account = {
                    id: safeId("account", newAccountType),
                    type: newAccountType,
                    current_value: Number(newValue) || 0,
                    missing_holdings_confirmed: true,
                  };
                  const placeholderIndex = state.accounts.findIndex(
                    (item) => numberValue(item.current_value) <= 0,
                  );
                  save({
                    accounts:
                      placeholderIndex >= 0
                        ? replaceAt(state.accounts, placeholderIndex, account)
                        : [...state.accounts, account],
                  });
                  setNewValue("");
                }}
                variant="secondary"
              >
                <Plus size={16} />
                Account
              </Button>
            </div>
          </div>
        ) : null}

        {activeSection === "goals" ? (
          <div className="space-y-3">
            {state.goals.map((goal, index) => (
              <div className="grid grid-cols-[1fr_120px_auto] gap-2 max-md:grid-cols-1" key={stringValue(goal.id, `goal-${index}`)}>
                <ReviewInput
                  label="Goal name"
                  value={stringValue(goal.name)}
                  source={sources.get(`goals[${index}].name`)}
                  onSave={(value, reason) => save({ goals: replaceAt(state.goals, index, { ...goal, name: value }) }, reason, true)}
                />
                <ReviewInput
                  label="Horizon years"
                  type="number"
                  value={String(numberValue(goal.time_horizon_years, 0))}
                  source={sources.get(`goals[${index}].time_horizon_years`)}
                  onSave={(value, reason) =>
                    save({ goals: replaceAt(state.goals, index, { ...goal, time_horizon_years: Number(value) || 0 }) }, reason, true)
                  }
                />
                <Button onClick={() => save({ goals: removeAt(state.goals, index) }, "advisor deleted goal", true)} variant="secondary">
                  Delete
                </Button>
              </div>
            ))}
            <div className="grid grid-cols-[1fr_auto] gap-2 max-md:grid-cols-1">
              <input className="min-h-10 rounded-md border border-slate-200 px-3 text-sm" onChange={(event) => setNewGoalName(event.target.value)} value={newGoalName} />
              <Button
                disabled={!newGoalName.trim()}
                onClick={() => {
                  const goal = {
                    id: safeId("goal", newGoalName),
                    name: newGoalName.trim(),
                    time_horizon_years: 5,
                  };
                  const placeholderIndex = state.goals.findIndex(
                    (item) => !stringValue(item.name) || numberValue(item.time_horizon_years) <= 0,
                  );
                  save({
                    goals:
                      placeholderIndex >= 0
                        ? replaceAt(state.goals, placeholderIndex, goal)
                        : [...state.goals, goal],
                  });
                  setNewGoalName("Retirement");
                }}
                variant="secondary"
              >
                <Plus size={16} />
                Goal
              </Button>
            </div>
          </div>
        ) : null}

        {activeSection === "goal_account_mapping" ? (
          <div className="space-y-3">
            {state.goal_account_links.map((link, index) => (
              <div className="grid grid-cols-[1fr_auto] gap-3 rounded-md border border-slate-100 px-3 py-3 text-sm" key={`${link.goal_id}-${link.account_id}-${index}`}>
                <div>
                  <div className="font-semibold">{labelForId(state.goals, link.goal_id, "Goal")} → {labelForId(state.accounts, link.account_id, "Account")}</div>
                  <div className="mt-1 text-slate-500">{currency.format(numberValue(link.allocated_amount))}</div>
                </div>
                <Button onClick={() => save({ goal_account_links: removeAt(state.goal_account_links, index) }, "advisor deleted mapping", true)} variant="secondary">
                  Delete
                </Button>
              </div>
            ))}
            <Button
              disabled={!state.goals.length || !state.accounts.length}
              onClick={() =>
                save({
                  goal_account_links: [
                    ...state.goal_account_links,
                    {
                      goal_id: stringValue(state.goals[0].id),
                      account_id: stringValue(
                        (state.accounts.find((account) => numberValue(account.current_value) > 0) ??
                          state.accounts[0]).id,
                      ),
                      allocated_amount: numberValue(
                        (state.accounts.find((account) => numberValue(account.current_value) > 0) ??
                          state.accounts[0]).current_value,
                      ),
                    },
                  ],
                })
              }
              variant="secondary"
            >
              <Link2 size={16} />
              Confirm First Goal/Account Mapping
            </Button>
          </div>
        ) : null}

        {activeSection === "risk" ? (
          <div className="grid grid-cols-2 gap-3 max-md:grid-cols-1">
            <ReviewInput
              label="Household risk"
              type="number"
              min={1}
              max={5}
              value={String(numberValue(state.risk.household_score ?? state.household.household_risk_score, 3))}
              source={sources.get("risk.household_score")}
              onSave={(value, reason) =>
                save(
                  {
                    risk: { ...state.risk, household_score: Number(value) || 3 },
                    household: { ...state.household, household_risk_score: Number(value) || 3 },
                  },
                  reason,
                  true,
                )
              }
            />
          </div>
        ) : null}

        {state.conflicts.length ? (
          <div className="space-y-2 rounded-md border border-[#fff1c7] bg-[#fffbeb] p-3">
            <div className="text-xs font-bold uppercase tracking-wider text-[#775b0b]">Conflicts</div>
            {state.conflicts.map((conflict, index) => (
              <div className="rounded-md bg-white px-3 py-2 text-sm" key={`${stringValue(conflict.field)}-${index}`}>
                <div className="font-semibold">
                  {stringValue(conflict.label, labelForField(stringValue(conflict.field)))}
                </div>
                <div className="mt-1 text-xs text-slate-500">{Array.isArray(conflict.values) ? conflict.values.join(" / ") : "Multiple values"}</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Button
                    onClick={() => {
                      const reason = window.prompt("Reason for resolving this conflict");
                      if (reason) {
                        save(
                          { conflicts: replaceAt(state.conflicts, index, { ...conflict, resolved: true, resolution: "kept_current" }) },
                          reason,
                          true,
                        );
                      }
                    }}
                    variant="secondary"
                  >
                    Keep Current
                  </Button>
                  <Button
                    onClick={() => {
                      const reason = window.prompt("Reason for marking this unknown");
                      if (reason) {
                        save(
                          {
                            conflicts: replaceAt(state.conflicts, index, { ...conflict, resolved: true, resolution: "marked_unknown" }),
                            unknowns: [...state.unknowns, { section: sectionForField(stringValue(conflict.field)), field: conflict.field, required: true }],
                          },
                          reason,
                          true,
                        );
                      }
                    }}
                    variant="secondary"
                  >
                    Mark Unknown
                  </Button>
                </div>
              </div>
            ))}
          </div>
        ) : null}
        {mutation.error ? <ErrorLine message={mutation.error.message} /> : null}
        {reconcileMutation.error ? <ErrorLine message={reconcileMutation.error.message} /> : null}
      </div>
    </section>
  );
}

function ReviewInput({
  label,
  value,
  onSave,
  source,
  type = "text",
  min,
  max,
}: {
  label: string;
  value: string;
  onSave: (value: string, reason?: string) => void;
  source?: Record<string, unknown>;
  type?: "text" | "number";
  min?: number;
  max?: number;
}) {
  const [draft, setDraft] = useState(value);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  useEffect(() => setDraft(value), [value]);
  return (
    <label className="space-y-1 text-sm">
      <span className="text-xs font-bold uppercase tracking-wider text-slate-500">{label}</span>
      <input
        className="min-h-10 w-full rounded-md border border-slate-200 px-3"
        onBlur={() => {
          if (draft !== value) {
            const reason = source ? window.prompt(`Reason for overriding ${label}`) ?? "" : "";
            onSave(draft, reason);
          }
        }}
        onChange={(event) => setDraft(event.target.value)}
        max={max}
        min={min}
        type={type}
        value={draft}
      />
      {source ? (
        <div className="rounded-md bg-mist px-2 py-2 text-xs text-slate-600">
          <button className="font-semibold text-spruce" onClick={() => setEvidenceOpen(!evidenceOpen)} type="button">
            {source.document_name ? String(source.document_name) : "Source"} · {source.confidence ? String(source.confidence) : "unknown"}
          </button>
          {evidenceOpen ? (
            <div className="mt-2 space-y-1">
              <div>{source.source_page ? `Page ${String(source.source_page)}` : String(source.source_location ?? "")}</div>
              <div className="rounded bg-white px-2 py-1">{String(source.evidence_quote ?? "No evidence quote.")}</div>
            </div>
          ) : null}
        </div>
      ) : null}
    </label>
  );
}

function SectionApprovalPanel({
  workspace,
  state,
  readiness,
  onChanged,
}: {
  workspace: ReviewWorkspace;
  state: ReviewedClientState;
  readiness: Readiness;
  onChanged: () => void;
}) {
  const [statuses, setStatuses] = useState<Record<string, ApprovalStatus>>({});
  const [notes, setNotes] = useState<Record<string, string>>({});
  const mutation = useMutation({
    mutationFn: (section: string) =>
      approveReviewSection(
        workspace.external_id,
        section,
        statuses[section] ?? "approved",
        notes[section] ?? "",
      ),
    onSuccess: onChanged,
  });
  const approvals = new Map(workspace.section_approvals.map((approval) => [approval.section, approval.status]));

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4 shadow-soft">
      <PanelTitle icon={<CheckCircle2 size={17} />} title="Section Approval" />
      <div className="mt-4 space-y-3">
        {requiredSections.map((section) => (
          <div className="rounded-md border border-slate-200 px-3 py-3" key={section}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="font-semibold">{humanize(section)}</div>
                <div className="mt-1 text-xs text-slate-500">
                  {sectionBlockers(state, readiness, section).length
                    ? `${sectionBlockers(state, readiness, section).length} blocker(s)`
                    : "No blockers detected"}
                </div>
              </div>
              <StatusBadge status={approvals.get(section) ?? "needs_attention"} />
            </div>
            <div className="mt-3 grid grid-cols-[220px_1fr_auto] gap-2 max-lg:grid-cols-1">
              <select
                className="min-h-10 rounded-md border border-slate-200 px-3 text-sm"
                onChange={(event) =>
                  setStatuses({ ...statuses, [section]: event.target.value as ApprovalStatus })
                }
                value={statuses[section] ?? "approved"}
              >
                <option value="approved">Approved</option>
                <option value="approved_with_unknowns">Approved with unknowns</option>
                <option value="needs_attention">Needs attention</option>
                <option value="not_ready_for_recommendation">Not ready</option>
              </select>
              <input
                className="min-h-10 rounded-md border border-slate-200 px-3 text-sm"
                onChange={(event) => setNotes({ ...notes, [section]: event.target.value })}
                placeholder="Approval note"
                value={notes[section] ?? ""}
              />
              <Button
                aria-label={`Save ${humanize(section)} approval`}
                disabled={mutation.isPending}
                onClick={() => mutation.mutate(section)}
                variant="secondary"
              >
                Save Approval
              </Button>
            </div>
          </div>
        ))}
      </div>
      {mutation.error ? <div className="mt-3"><ErrorLine message={mutation.error.message} /></div> : null}
    </section>
  );
}

function StateSummary({ state }: { state: ReviewedClientState }) {
  return (
    <section className="rounded-md border border-slate-200 bg-white shadow-soft">
      <PanelTitle icon={<ShieldCheck size={17} />} title="Reviewed State" />
      <div className="grid grid-cols-3 gap-3 p-4 max-lg:grid-cols-1">
        <StateBlock title="People" values={state.people.map((person) => stringValue(person.name, "Unnamed"))} />
        <StateBlock
          title="Accounts"
          values={state.accounts.map((account) => `${stringValue(account.type, "Account")} ${currency.format(numberValue(account.current_value))}`)}
        />
        <StateBlock title="Goals" values={state.goals.map((goal) => stringValue(goal.name, "Goal"))} />
      </div>
      {state.conflicts.length ? (
        <div className="border-t border-slate-100 px-4 py-3">
          <div className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-500">Conflicts</div>
          <div className="space-y-2">
            {state.conflicts.map((conflict, index) => (
              <div className="rounded-md bg-[#fff1c7] px-3 py-2 text-sm text-[#775b0b]" key={index}>
                {stringValue(conflict.label, labelForField(stringValue(conflict.field, "conflict")))}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}

function MatchCommitPanel({
  workspace,
  matches,
  clients,
  readiness,
  matchesError,
  onFindMatches,
  onOpenClient,
}: {
  workspace: ReviewWorkspace;
  matches: MatchCandidate[];
  clients: HouseholdSummary[];
  readiness: Readiness;
  matchesError?: string;
  onFindMatches: () => void;
  onOpenClient: (id: string) => void;
}) {
  const queryClient = useQueryClient();
  const commitMutation = useMutation({
    mutationFn: (householdId?: string) => commitReviewWorkspace(workspace.external_id, householdId),
    onSuccess: (payload) => {
      void queryClient.invalidateQueries({ queryKey: ["clients"] });
      void queryClient.invalidateQueries({ queryKey: ["review-workspace", workspace.external_id] });
      void queryClient.invalidateQueries({ queryKey: ["review-workspaces"] });
      onOpenClient(payload.household_id);
    },
  });
  const isLinked = Boolean(workspace.linked_household_id) || workspace.status === "committed";
  const approvals = new Map(workspace.section_approvals.map((approval) => [approval.section, approval.status]));
  const requiredApproved = requiredSections.every((section) => approvals.get(section) === "approved");
  const canCommit = readiness.engine_ready && readiness.construction_ready && requiredApproved;
  const likelyMatches = isLinked
    ? []
    : (matches.length ? matches : fallbackMatches(workspace, clients)).filter(
        (candidate) => candidate.household_id !== workspace.linked_household_id,
      );

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4 shadow-soft">
      <PanelTitle icon={<Link2 size={17} />} title="Link Or Create" />
      {!isLinked ? (
        <>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button onClick={onFindMatches} variant="secondary">
              <RefreshCw size={16} />
              Find Matches
            </Button>
            <Button
              disabled={!canCommit || commitMutation.isPending}
              onClick={() => commitMutation.mutate(undefined)}
            >
              <Plus size={16} />
              Create Household
            </Button>
          </div>
          {!requiredApproved ? (
            <div className="mt-3 rounded-md bg-[#fff1c7] px-3 py-2 text-sm text-[#775b0b]">
              Required sections must be approved before commit.
            </div>
          ) : null}
          {requiredApproved && (!readiness.engine_ready || !readiness.construction_ready) ? (
            <div className="mt-3 rounded-md bg-[#fff1c7] px-3 py-2 text-sm text-[#775b0b]">
              Engine and construction readiness must both pass before commit.
            </div>
          ) : null}
          <div className="mt-4 space-y-2">
            {likelyMatches.length ? (
              likelyMatches.map((candidate) => (
                <div className="rounded-md border border-slate-200 px-3 py-3" key={candidate.household_id}>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <div className="font-semibold">{candidate.display_name}</div>
                      <div className="mt-1 text-xs text-slate-500">
                        {candidate.confidence}% confidence
                        {candidate.reasons.length ? ` - ${candidate.reasons.join(", ")}` : ""}
                      </div>
                    </div>
                    <Button
                      disabled={!canCommit || commitMutation.isPending}
                      onClick={() => commitMutation.mutate(candidate.household_id)}
                      variant="secondary"
                    >
                      <Link2 size={16} />
                      Link
                    </Button>
                  </div>
                </div>
              ))
            ) : (
              <div className="rounded-md bg-mist px-3 py-3 text-sm text-slate-600">No likely matches loaded.</div>
            )}
          </div>
        </>
      ) : null}
      {workspace.linked_household_id ? (
        <Button className="mt-4" onClick={() => onOpenClient(workspace.linked_household_id!)} variant="secondary">
          Open Linked Client
        </Button>
      ) : null}
      {matchesError ? <div className="mt-3"><ErrorLine message={matchesError} /></div> : null}
      {commitMutation.error ? <div className="mt-3"><ErrorLine message={commitMutation.error.message} /></div> : null}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white px-4 py-3 shadow-soft">
      <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</div>
      <div className="mt-1 text-xl font-semibold capitalize">{value}</div>
    </div>
  );
}

function PanelTitle({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-spruce">{icon}</span>
      <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">{title}</h3>
    </div>
  );
}

function StateBlock({ title, values }: { title: string; values: string[] }) {
  return (
    <div className="rounded-md bg-mist px-3 py-3">
      <div className="text-xs font-bold uppercase tracking-wider text-slate-500">{title}</div>
      <div className="mt-2 space-y-1 text-sm">
        {values.length ? values.map((value, index) => <div key={`${value}-${index}`}>{value}</div>) : <div className="text-slate-500">Empty</div>}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const color = statusBadgeColor(status);
  return (
    <span className={`inline-flex rounded-full px-2 py-1 text-xs font-bold uppercase ${color}`}>
      {humanize(status)}
    </span>
  );
}

function ErrorLine({ message }: { message: string }) {
  return <div className="rounded-md bg-[#ffe0d2] px-3 py-2 text-sm text-[#7d3b20]">{message}</div>;
}

function normalizeState(state: Partial<ReviewedClientState>): ReviewedClientState {
  return {
    schema_version: state.schema_version ?? "reviewed_client_state.v1",
    household: state.household ?? {},
    people: state.people ?? [],
    accounts: state.accounts ?? [],
    goals: state.goals ?? [],
    goal_account_links: state.goal_account_links ?? [],
    risk: state.risk ?? {},
    planning: state.planning ?? {},
    behavioral_notes: state.behavioral_notes ?? {},
    unknowns: state.unknowns ?? [],
    conflicts: state.conflicts ?? [],
    source_summary: state.source_summary ?? [],
    field_sources:
      (state as Partial<ReviewedClientState> & {
        field_sources?: Record<string, Record<string, unknown>>;
      }).field_sources ?? {},
    readiness: normalizeReadiness(state.readiness, undefined),
  };
}

function normalizeReadiness(primary?: Partial<Readiness>, fallback?: Partial<Readiness>): Readiness {
  return {
    engine_ready: Boolean(primary?.engine_ready ?? fallback?.engine_ready),
    construction_ready: Boolean(primary?.construction_ready ?? fallback?.construction_ready),
    kyc_compliance_ready: Boolean(primary?.kyc_compliance_ready ?? fallback?.kyc_compliance_ready),
    missing: primary?.missing ?? fallback?.missing ?? [],
    construction_missing: primary?.construction_missing ?? fallback?.construction_missing ?? [],
  };
}

function statusBadgeColor(status: string): string {
  if (["engine_ready", "committed", "approved", "completed", "reconciled"].includes(status)) {
    return "bg-mist text-spruce";
  }
  if (["processing", "queued", "review_ready", "uploaded", "text_extracted", "facts_extracted"].includes(status)) {
    return "bg-[#fff1c7] text-[#775b0b]";
  }
  if (["failed", "unsupported", "needs_review", "needs_attention"].includes(status)) {
    return "bg-[#ffe0d2] text-[#7d3b20]";
  }
  return "bg-slate-100 text-slate-600";
}

function humanize(value: string): string {
  return value.replace(/_/g, " ");
}

function labelForField(field: string): string {
  const labels: Record<string, string> = {
    "household.display_name": "Household name",
    "household.household_type": "Household type",
    "risk.household_score": "Household risk score",
  };
  if (labels[field]) {
    return labels[field];
  }
  return field
    .replace(/\[\d+\]/g, "")
    .replace(/[._]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^./, (character) => character.toUpperCase());
}

function stringValue(value: unknown, fallback = ""): string {
  if (typeof value === "string") {
    return value;
  }
  if (value === null || value === undefined) {
    return fallback;
  }
  return String(value);
}

function numberValue(value: unknown, fallback = 0): number {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
}

function safeId(prefix: string, value: string): string {
  const slug = value.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
  return `${prefix}_${slug || "item"}_${Date.now()}`;
}

function formatBytes(bytes: number): string {
  if (!bytes) {
    return "0 B";
  }
  const units = ["B", "KB", "MB", "GB"];
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** exponent;
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[exponent]}`;
}

function replaceAt<T>(items: T[], index: number, value: T): T[] {
  return items.map((item, itemIndex) => (itemIndex === index ? value : item));
}

function removeAt<T>(items: T[], index: number): T[] {
  return items.filter((_, itemIndex) => itemIndex !== index);
}

function sourceMap(state: ReviewedClientState): Map<string, Record<string, unknown>> {
  return new Map(Object.entries(state.field_sources ?? {}));
}

function labelForId(items: Array<Record<string, unknown>>, id: unknown, fallback: string): string {
  const item = items.find((candidate) => stringValue(candidate.id) === stringValue(id));
  return stringValue(item?.name ?? item?.type, fallback);
}

function sectionForField(field: string): string {
  if (field.startsWith("people")) {
    return "people";
  }
  if (field.startsWith("accounts") || field.startsWith("holdings")) {
    return "accounts";
  }
  if (field.startsWith("goals")) {
    return "goals";
  }
  if (field.startsWith("goal_account")) {
    return "goal_account_mapping";
  }
  if (field.startsWith("risk")) {
    return "risk";
  }
  return "household";
}

function sectionBlockers(state: ReviewedClientState, readiness: Readiness, section: string): string[] {
  const missing = readiness.missing
    .filter((item) => item.section === section)
    .map((item) => item.label);
  const construction = readiness.construction_missing
    .filter((item) => item.section === section)
    .map((item) => item.label);
  const conflicts = state.conflicts
    .filter((conflict) => !conflict.resolved && sectionForField(stringValue(conflict.field)) === section)
    .map((conflict) => `Conflict: ${stringValue(conflict.field)}`);
  const unknowns = state.unknowns
    .filter((unknown) => {
      if (typeof unknown === "string") {
        return sectionForField(unknown) === section;
      }
      return Boolean(unknown.required) && (unknown.section === section || sectionForField(stringValue(unknown.field)) === section);
    })
    .map((unknown) => (typeof unknown === "string" ? unknown : stringValue(unknown.label ?? unknown.field, "Unknown")));
  return [...missing, ...construction, ...conflicts, ...unknowns];
}

function fallbackMatches(workspace: ReviewWorkspace, clients: HouseholdSummary[]): MatchCandidate[] {
  const displayName = stringValue(workspace.reviewed_state.household?.display_name, workspace.label);
  return clients
    .filter(
      (client) =>
        client.id !== workspace.linked_household_id &&
        client.display_name.toLowerCase() === displayName.toLowerCase(),
    )
    .map((client) => ({
      household_id: client.id,
      display_name: client.display_name,
      confidence: 60,
      reasons: ["household name"],
    }));
}
