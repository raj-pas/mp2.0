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
  const mutation = useMutation({
    mutationFn: () => createReviewWorkspace(label.trim()),
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
      <div className="grid grid-cols-4 gap-3 max-xl:grid-cols-2 max-sm:grid-cols-1">
        <Metric label="Status" value={humanize(workspace.status)} />
        <Metric label="Documents" value={String(workspace.documents.length)} />
        <Metric label="Facts" value={String(facts.length)} />
        <Metric label="Engine Ready" value={readiness.engine_ready ? "Yes" : "No"} />
      </div>

      <div className="grid grid-cols-[0.9fr_1.1fr] gap-5 max-2xl:grid-cols-1">
        <div className="space-y-5">
          <UploadPanel workspace={workspace} onChanged={invalidateWorkspace} />
          <DocumentPanel documents={workspace.documents} onChanged={invalidateWorkspace} workspaceId={workspace.external_id} />
          <JobPanel jobs={workspace.processing_jobs} />
          <FactPanel facts={facts} />
        </div>
        <div className="space-y-5">
          <ReadinessPanel readiness={readiness} />
          <QuickFillPanel state={state} workspaceId={workspace.external_id} />
          <SectionApprovalPanel workspace={workspace} onChanged={invalidateWorkspace} />
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
            Uploaded {mutation.data.uploaded.length}; duplicates {mutation.data.duplicates.length}.
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

function JobPanel({ jobs }: { jobs: ReviewWorkspace["processing_jobs"] }) {
  const activeJobs = jobs.filter((job) => ["queued", "processing"].includes(job.status));
  return (
    <section className="rounded-md border border-slate-200 bg-white shadow-soft">
      <PanelTitle icon={<RefreshCw size={17} />} title="Worker Queue" />
      <div className="divide-y divide-slate-100">
        {activeJobs.length ? (
          activeJobs.map((job) => (
            <div className="grid grid-cols-[1fr_auto] gap-3 px-4 py-3 text-sm" key={job.id}>
              <div>
                <div className="font-semibold">{humanize(job.job_type)}</div>
                <div className="mt-1 text-xs text-slate-500">
                  Attempt {job.attempts}/{job.max_attempts}
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
                <span className="font-semibold">{fact.field}</span>
                <span className="rounded-full bg-mist px-2 py-1 text-xs font-semibold uppercase text-slate-600">
                  {fact.confidence}
                </span>
              </div>
              <div className="mt-2 break-words rounded-md bg-[#fbfaf5] px-3 py-2 text-xs text-slate-700">
                {fact.evidence_quote || JSON.stringify(fact.value)}
              </div>
              <div className="mt-2 text-xs text-slate-500">
                {fact.document_name} {fact.source_location ? `- ${fact.source_location}` : ""}
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
        <StatusBadge status={readiness.engine_ready ? "engine_ready" : "needs_review"} />
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 max-sm:grid-cols-1">
        <div className="rounded-md bg-mist px-3 py-3">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-500">Engine</div>
          <div className="mt-1 text-lg font-semibold">{readiness.engine_ready ? "Ready" : "Incomplete"}</div>
        </div>
        <div className="rounded-md bg-mist px-3 py-3">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-500">KYC</div>
          <div className="mt-1 text-lg font-semibold">
            {readiness.kyc_compliance_ready ? "Ready" : "Separate Review"}
          </div>
        </div>
      </div>
      {readiness.missing.length ? (
        <div className="mt-4 space-y-2">
          {readiness.missing.map((item) => (
            <div className="rounded-md border border-slate-200 px-3 py-2 text-sm" key={`${item.section}-${item.label}`}>
              <span className="font-semibold">{humanize(item.section)}</span>: {item.label}
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function QuickFillPanel({ workspaceId, state }: { workspaceId: string; state: ReviewedClientState }) {
  const queryClient = useQueryClient();
  const [householdName, setHouseholdName] = useState(stringValue(state.household.display_name));
  const [riskScore, setRiskScore] = useState(String(numberValue(state.risk.household_score ?? state.household.household_risk_score, 3)));
  const [memberName, setMemberName] = useState("");
  const [memberAge, setMemberAge] = useState("62");
  const [accountType, setAccountType] = useState("RRSP");
  const [accountValue, setAccountValue] = useState("");
  const [goalName, setGoalName] = useState("Retirement");
  const [goalHorizon, setGoalHorizon] = useState("5");
  const mutation = useMutation({
    mutationFn: (patch: Partial<ReviewedClientState>) => patchReviewState(workspaceId, patch),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["review-workspace", workspaceId] });
      void queryClient.invalidateQueries({ queryKey: ["review-workspaces"] });
    },
  });

  useEffect(() => {
    setHouseholdName(stringValue(state.household.display_name));
    setRiskScore(String(numberValue(state.risk.household_score ?? state.household.household_risk_score, 3)));
  }, [state.household.display_name, state.household.household_risk_score, state.risk.household_score]);

  const addMember = () => {
    if (!memberName.trim()) {
      return;
    }
    mutation.mutate({
      people: [
        ...state.people,
        { id: safeId("person", memberName), name: memberName.trim(), age: Number(memberAge) || 62 },
      ],
    });
    setMemberName("");
  };
  const addAccount = () => {
    if (!accountValue.trim()) {
      return;
    }
    mutation.mutate({
      accounts: [
        ...state.accounts,
        {
          id: safeId("account", accountType),
          type: accountType,
          current_value: Number(accountValue) || 0,
          missing_holdings_confirmed: true,
        },
      ],
    });
    setAccountValue("");
  };
  const addGoal = () => {
    if (!goalName.trim()) {
      return;
    }
    mutation.mutate({
      goals: [
        ...state.goals,
        { id: safeId("goal", goalName), name: goalName.trim(), time_horizon_years: Number(goalHorizon) || 5 },
      ],
    });
    setGoalName("Retirement");
  };
  const confirmMapping = () => {
    const goal = state.goals[0];
    const account = state.accounts[0];
    if (!goal || !account) {
      return;
    }
    mutation.mutate({
      goal_account_links: [
        ...state.goal_account_links,
        {
          goal_id: stringValue(goal.id),
          account_id: stringValue(account.id),
          allocated_amount: numberValue(account.current_value),
        },
      ],
    });
  };

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4 shadow-soft">
      <PanelTitle icon={<Plus size={17} />} title="Quick Fill" />
      <div className="mt-4 grid grid-cols-2 gap-3 max-lg:grid-cols-1">
        <label className="space-y-1 text-sm">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Household</span>
          <input
            className="min-h-10 w-full rounded-md border border-slate-200 px-3"
            onChange={(event) => setHouseholdName(event.target.value)}
            value={householdName}
          />
        </label>
        <label className="space-y-1 text-sm">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Risk Score</span>
          <input
            className="min-h-10 w-full rounded-md border border-slate-200 px-3"
            max={10}
            min={1}
            onChange={(event) => setRiskScore(event.target.value)}
            type="number"
            value={riskScore}
          />
        </label>
        <Button
          className="col-span-2 max-lg:col-span-1"
          disabled={mutation.isPending}
          onClick={() =>
            mutation.mutate({
              household: {
                ...state.household,
                display_name: householdName.trim(),
                household_type: stringValue(state.household.household_type, "couple"),
                household_risk_score: Number(riskScore) || 3,
              },
              risk: { ...state.risk, household_score: Number(riskScore) || 3 },
            })
          }
          variant="secondary"
        >
          <CheckCircle2 size={16} />
          Save Basics
        </Button>
      </div>

      <div className="mt-4 grid grid-cols-[1fr_82px_auto] gap-2 max-md:grid-cols-1">
        <input
          className="min-h-10 rounded-md border border-slate-200 px-3 text-sm"
          onChange={(event) => setMemberName(event.target.value)}
          placeholder="Member name"
          value={memberName}
        />
        <input
          className="min-h-10 rounded-md border border-slate-200 px-3 text-sm"
          onChange={(event) => setMemberAge(event.target.value)}
          placeholder="Age"
          type="number"
          value={memberAge}
        />
        <Button disabled={mutation.isPending || !memberName.trim()} onClick={addMember} variant="secondary">
          <Plus size={16} />
          Member
        </Button>
      </div>

      <div className="mt-3 grid grid-cols-[120px_1fr_auto] gap-2 max-md:grid-cols-1">
        <input
          className="min-h-10 rounded-md border border-slate-200 px-3 text-sm"
          onChange={(event) => setAccountType(event.target.value)}
          value={accountType}
        />
        <input
          className="min-h-10 rounded-md border border-slate-200 px-3 text-sm"
          onChange={(event) => setAccountValue(event.target.value)}
          placeholder="Account value"
          type="number"
          value={accountValue}
        />
        <Button disabled={mutation.isPending || !accountValue.trim()} onClick={addAccount} variant="secondary">
          <Plus size={16} />
          Account
        </Button>
      </div>

      <div className="mt-3 grid grid-cols-[1fr_90px_auto] gap-2 max-md:grid-cols-1">
        <input
          className="min-h-10 rounded-md border border-slate-200 px-3 text-sm"
          onChange={(event) => setGoalName(event.target.value)}
          value={goalName}
        />
        <input
          className="min-h-10 rounded-md border border-slate-200 px-3 text-sm"
          onChange={(event) => setGoalHorizon(event.target.value)}
          type="number"
          value={goalHorizon}
        />
        <Button disabled={mutation.isPending || !goalName.trim()} onClick={addGoal} variant="secondary">
          <Plus size={16} />
          Goal
        </Button>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Button
          disabled={mutation.isPending || !state.accounts.length || !state.goals.length}
          onClick={confirmMapping}
          variant="secondary"
        >
          <Link2 size={16} />
          Confirm Mapping
        </Button>
        {mutation.error ? <ErrorLine message={mutation.error.message} /> : null}
      </div>
    </section>
  );
}

function SectionApprovalPanel({ workspace, onChanged }: { workspace: ReviewWorkspace; onChanged: () => void }) {
  const mutation = useMutation({
    mutationFn: (section: string) => approveReviewSection(workspace.external_id, section),
    onSuccess: onChanged,
  });
  const approvals = new Map(workspace.section_approvals.map((approval) => [approval.section, approval.status]));

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4 shadow-soft">
      <PanelTitle icon={<CheckCircle2 size={17} />} title="Section Approval" />
      <div className="mt-4 grid grid-cols-2 gap-2 max-md:grid-cols-1">
        {requiredSections.map((section) => (
          <button
            className="flex min-h-11 items-center justify-between gap-3 rounded-md border border-slate-200 px-3 text-left text-sm hover:border-spruce"
            disabled={mutation.isPending}
            key={section}
            onClick={() => mutation.mutate(section)}
            type="button"
          >
            <span className="font-semibold">{humanize(section)}</span>
            <StatusBadge status={approvals.get(section) ?? "needs_attention"} />
          </button>
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
                {stringValue(conflict.field, "conflict")}
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
              disabled={!readiness.engine_ready || commitMutation.isPending}
              onClick={() => commitMutation.mutate(undefined)}
            >
              <Plus size={16} />
              Create Household
            </Button>
          </div>
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
                      disabled={!readiness.engine_ready || commitMutation.isPending}
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
    readiness: normalizeReadiness(state.readiness, undefined),
  };
}

function normalizeReadiness(primary?: Partial<Readiness>, fallback?: Partial<Readiness>): Readiness {
  return {
    engine_ready: Boolean(primary?.engine_ready ?? fallback?.engine_ready),
    kyc_compliance_ready: Boolean(primary?.kyc_compliance_ready ?? fallback?.kyc_compliance_ready),
    missing: primary?.missing ?? fallback?.missing ?? [],
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
