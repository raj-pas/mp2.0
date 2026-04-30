import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  ArrowRight,
  BarChart3,
  CheckCircle2,
  Database,
  Download,
  FileText,
  LogIn,
  LogOut,
  RefreshCw,
  ShieldCheck,
  Target,
  WalletCards,
  X,
} from "lucide-react";
import { useMemo, useState } from "react";

import {
  declinePortfolioRun,
  exportPortfolioAudit,
  fetchClient,
  fetchClients,
  fetchSession,
  generatePortfolio,
  login,
  logout,
} from "./api";
import { CmaWorkbench } from "./CmaWorkbench";
import { Button } from "./components/ui/button";
import { ReviewShell } from "./ReviewShell";
import type {
  Account,
  Allocation,
  Goal,
  HouseholdDetail,
  HouseholdSummary,
  LinkRecommendation,
  PortfolioAuditExport,
  PortfolioRun,
} from "./types";

const currency = new Intl.NumberFormat("en-CA", {
  style: "currency",
  currency: "CAD",
  maximumFractionDigits: 0,
});

const percent = new Intl.NumberFormat("en-CA", {
  style: "percent",
  maximumFractionDigits: 1,
});

function App() {
  const [selectedClientId, setSelectedClientId] = useState<string>("hh_sandra_mike_chen");
  const [mode, setMode] = useState<"clients" | "review" | "cma">("clients");
  const queryClient = useQueryClient();
  const session = useQuery({
    queryKey: ["session"],
    queryFn: fetchSession,
  });
  const isAuthenticated = Boolean(session.data?.authenticated);
  const userRole = session.data?.user?.role ?? "";
  const canAccessClients = isAuthenticated && userRole !== "financial_analyst";
  const clients = useQuery({
    queryKey: ["clients"],
    queryFn: fetchClients,
    enabled: canAccessClients,
  });
  const selectedClient = useQuery({
    queryKey: ["client", selectedClientId],
    queryFn: () => fetchClient(selectedClientId),
    enabled: Boolean(selectedClientId) && canAccessClients,
  });
  const portfolioMutation = useMutation({
    mutationFn: () => generatePortfolio(selectedClientId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["client", selectedClientId] });
    },
  });
  const logoutMutation = useMutation({
    mutationFn: logout,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["session"] });
      void queryClient.removeQueries({ queryKey: ["clients"] });
      void queryClient.removeQueries({ queryKey: ["client"] });
      setMode("clients");
    },
  });

  const currentOutput = useMemo(() => {
    if (portfolioMutation.data?.output.household_id === selectedClientId) {
      return portfolioMutation.data;
    }
    return selectedClient.data?.latest_portfolio_run ?? null;
  }, [portfolioMutation.data, selectedClient.data?.latest_portfolio_run, selectedClientId]);

  const selectClient = (id: string) => {
    portfolioMutation.reset();
    setSelectedClientId(id);
  };

  return (
    <main className="min-h-screen bg-[#f7f8f5] text-ink">
      <div className="grid min-h-screen grid-cols-[280px_1fr] max-lg:grid-cols-1">
        <aside className="border-r border-slate-200 bg-white px-5 py-5 max-lg:border-b max-lg:border-r-0">
          <div className="mb-6 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-spruce text-white">
              <BarChart3 size={20} />
            </div>
            <div>
              <h1 className="text-lg font-semibold">MP2.0 Advisor</h1>
              <p className="text-xs text-slate-500">Secure local scaffold</p>
            </div>
          </div>
          <div className={`mb-5 grid gap-2 ${userRole === "financial_analyst" ? "grid-cols-3" : "grid-cols-2"}`}>
            <ModeButton active={mode === "clients"} icon={<Database size={15} />} onClick={() => setMode("clients")}>
              Clients
            </ModeButton>
            <ModeButton active={mode === "review"} icon={<FileText size={15} />} onClick={() => setMode("review")}>
              Review
            </ModeButton>
            {userRole === "financial_analyst" ? (
              <ModeButton active={mode === "cma"} icon={<BarChart3 size={15} />} onClick={() => setMode("cma")}>
                CMA
              </ModeButton>
            ) : null}
          </div>
          <SessionStatus
            authenticated={Boolean(session.data?.authenticated)}
            email={session.data?.user?.email}
            isLoading={session.isLoading}
            isLoggingOut={logoutMutation.isPending}
            onLogout={() => logoutMutation.mutate()}
          />
          <ClientList
            authenticated={canAccessClients}
            clients={canAccessClients ? (clients.data ?? []) : []}
            isLoading={canAccessClients && clients.isLoading}
            selectedClientId={selectedClientId}
            onSelect={selectClient}
          />
        </aside>

        <section className="min-w-0 px-6 py-5">
          {mode === "cma" ? (
            session.isLoading ? (
              <EmptyState label="Checking session" />
            ) : isAuthenticated && userRole === "financial_analyst" ? (
              <CmaWorkbench />
            ) : (
              <EmptyState label="CMA Workbench is restricted" />
            )
          ) : mode === "review" ? (
            session.isLoading ? (
              <EmptyState label="Checking session" />
            ) : isAuthenticated ? (
              <ReviewShell
                onOpenClient={(id) => {
                  setSelectedClientId(id);
                  setMode("clients");
                  void queryClient.invalidateQueries({ queryKey: ["clients"] });
                  void queryClient.invalidateQueries({ queryKey: ["client", id] });
                }}
              />
            ) : (
              <LoginPanel />
            )
          ) : session.isLoading ? (
            <EmptyState label="Checking session" />
          ) : !isAuthenticated ? (
            <LoginPanel />
          ) : selectedClient.isLoading ? (
            <EmptyState label="Loading client" />
          ) : selectedClient.error ? (
            <EmptyState label="Backend unavailable" />
          ) : selectedClient.data ? (
            <AdvisorWorkspace
              client={selectedClient.data}
              error={portfolioMutation.error?.message}
              output={currentOutput}
              isGenerating={portfolioMutation.isPending}
              onGenerate={() => portfolioMutation.mutate()}
            />
          ) : (
            <EmptyState label="Select a client" />
          )}
        </section>
      </div>
    </main>
  );
}

function ModeButton({
  active,
  children,
  icon,
  onClick,
}: {
  active: boolean;
  children: React.ReactNode;
  icon: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-md border px-3 text-sm font-semibold ${
        active ? "border-spruce bg-mist text-ink" : "border-slate-200 bg-white text-slate-600 hover:border-slate-300"
      }`}
      onClick={onClick}
      type="button"
    >
      {icon}
      {children}
    </button>
  );
}

function SessionStatus({
  authenticated,
  email,
  isLoading,
  isLoggingOut,
  onLogout,
}: {
  authenticated: boolean;
  email?: string;
  isLoading: boolean;
  isLoggingOut: boolean;
  onLogout: () => void;
}) {
  return (
    <div className="mb-5 rounded-md border border-slate-200 bg-[#fbfaf5] px-3 py-3 text-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-xs font-bold uppercase tracking-wider text-slate-500">Session</div>
          <div className="mt-1 truncate font-semibold">
            {isLoading ? "Checking" : authenticated ? email : "Not signed in"}
          </div>
        </div>
        {authenticated ? (
          <button
            aria-label="Sign out"
            className="flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-600 hover:border-spruce"
            disabled={isLoggingOut}
            onClick={onLogout}
            type="button"
          >
            <LogOut size={16} />
          </button>
        ) : null}
      </div>
    </div>
  );
}

function LoginPanel() {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const mutation = useMutation({
    mutationFn: () => login(email.trim(), password),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["session"] });
      void queryClient.invalidateQueries({ queryKey: ["clients"] });
    },
  });

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-lg items-center">
      <section className="w-full rounded-md border border-slate-200 bg-white p-5 shadow-soft">
        <div className="mb-5 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-spruce text-white">
            <LogIn size={20} />
          </div>
          <div>
            <h2 className="text-xl font-semibold">Local Advisor Login</h2>
            <p className="text-sm text-slate-500">Secure review workspace access</p>
          </div>
        </div>
        <form
          className="space-y-3"
          onSubmit={(event) => {
            event.preventDefault();
            mutation.mutate();
          }}
        >
          <input
            className="min-h-11 w-full rounded-md border border-slate-200 px-3 outline-none focus:border-spruce"
            onChange={(event) => setEmail(event.target.value)}
            placeholder="Email"
            type="email"
            value={email}
          />
          <input
            className="min-h-11 w-full rounded-md border border-slate-200 px-3 outline-none focus:border-spruce"
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Password"
            type="password"
            value={password}
          />
          <Button className="w-full" disabled={!email.trim() || !password || mutation.isPending} type="submit">
            <LogIn size={16} />
            {mutation.isPending ? "Signing In" : "Sign In"}
          </Button>
          {mutation.error ? (
            <div className="rounded-md bg-[#ffe0d2] px-3 py-2 text-sm text-[#7d3b20]">
              {mutation.error.message}
            </div>
          ) : null}
        </form>
      </section>
    </div>
  );
}

function ClientList({
  authenticated,
  clients,
  isLoading,
  selectedClientId,
  onSelect,
}: {
  authenticated: boolean;
  clients: HouseholdSummary[];
  isLoading: boolean;
  selectedClientId: string;
  onSelect: (id: string) => void;
}) {
  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">Clients</h2>
        <Database size={16} className="text-slate-400" />
      </div>
      <div className="space-y-2">
        {!authenticated ? (
          <div className="rounded-md bg-mist px-3 py-3 text-sm text-slate-600">Sign in to view clients.</div>
        ) : isLoading ? (
          <div className="rounded-md bg-mist px-3 py-3 text-sm text-slate-600">Loading</div>
        ) : clients.length ? (
          clients.map((client) => (
            <button
              className={`w-full rounded-md border px-3 py-3 text-left transition ${
                selectedClientId === client.id
                  ? "border-spruce bg-mist"
                  : "border-slate-200 bg-white hover:border-slate-300"
              }`}
              key={client.id}
              onClick={() => onSelect(client.id)}
              type="button"
            >
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm font-semibold">{client.display_name}</span>
                <ArrowRight size={15} className="text-slate-400" />
              </div>
              <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
                <span>{client.goal_count} goals</span>
                <span>{formatCurrency(client.total_assets)}</span>
              </div>
            </button>
          ))
        ) : (
          <div className="rounded-md bg-mist px-3 py-3 text-sm text-slate-600">No clients</div>
        )}
      </div>
    </div>
  );
}

function AdvisorWorkspace({
  client,
  output,
  error,
  isGenerating,
  onGenerate,
}: {
  client: HouseholdDetail;
  output: PortfolioRun | null;
  error?: string;
  isGenerating: boolean;
  onGenerate: () => void;
}) {
  const [activeView, setActiveView] = useState<"household" | "account" | "goal">("household");
  const [selectedAccountId, setSelectedAccountId] = useState(client.accounts[0]?.id ?? "");
  const [selectedGoalId, setSelectedGoalId] = useState(client.goals[0]?.id ?? "");
  const [grouping, setGrouping] = useState<"account" | "goal">("account");
  const selectedAccount =
    client.accounts.find((account) => account.id === selectedAccountId) ?? client.accounts[0];
  const selectedGoal = client.goals.find((goal) => goal.id === selectedGoalId) ?? client.goals[0];

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Household</p>
          <h2 className="mt-1 text-3xl font-semibold">{client.display_name}</h2>
          <p className="mt-2 max-w-3xl text-sm text-slate-600">{client.notes}</p>
        </div>
        <Button disabled={isGenerating} onClick={onGenerate}>
          <RefreshCw size={16} className={isGenerating ? "animate-spin" : ""} />
          {isGenerating ? "Generating" : "Generate Portfolio"}
        </Button>
      </header>
      {error ? <div className="rounded-md bg-[#ffe0d2] px-4 py-3 text-sm text-[#7d3b20]">{error}</div> : null}

      <div className="grid grid-cols-4 gap-3 max-xl:grid-cols-2 max-sm:grid-cols-1">
        <Metric label="Total Assets" value={formatCurrency(client.total_assets)} />
        <Metric label="Household Risk" value={`${client.household_risk_score}/5`} />
        <Metric label="Goals" value={String(client.goals.length)} />
        <Metric label="Accounts" value={String(client.accounts.length)} />
      </div>

      <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-2">
        <ConsoleTab active={activeView === "household"} icon={<BarChart3 size={16} />} onClick={() => setActiveView("household")}>
          Household
        </ConsoleTab>
        <ConsoleTab active={activeView === "account"} icon={<WalletCards size={16} />} onClick={() => setActiveView("account")}>
          Account
        </ConsoleTab>
        <ConsoleTab active={activeView === "goal"} icon={<Target size={16} />} onClick={() => setActiveView("goal")}>
          Goal
        </ConsoleTab>
      </div>

      {activeView === "household" ? (
        <div className="grid grid-cols-[1.05fr_0.95fr] gap-5 max-xl:grid-cols-1">
          <div className="space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="inline-flex rounded-md border border-slate-200 bg-white p-1">
                <SegmentButton active={grouping === "account"} onClick={() => setGrouping("account")}>
                  Accounts
                </SegmentButton>
                <SegmentButton active={grouping === "goal"} onClick={() => setGrouping("goal")}>
                  Goals
                </SegmentButton>
              </div>
            </div>
            <HouseholdRollupSummary client={client} output={output} grouping={grouping} />
            <PeoplePanel client={client} />
            {grouping === "account" ? <AccountsPanel accounts={client.accounts} /> : <GoalsPanel goals={client.goals} />}
          </div>
          <PortfolioPanel client={client} output={output} runHistory={client.portfolio_runs} />
        </div>
      ) : activeView === "account" && selectedAccount ? (
        <AccountConsole
          account={selectedAccount}
          accounts={client.accounts}
          goals={client.goals}
          output={output}
          onSelectAccount={setSelectedAccountId}
        />
      ) : activeView === "goal" && selectedGoal ? (
        <GoalConsole
          accounts={client.accounts}
          goal={selectedGoal}
          goals={client.goals}
          output={output}
          onSelectGoal={setSelectedGoalId}
        />
      ) : null}
    </div>
  );
}

function ConsoleTab({
  active,
  children,
  icon,
  onClick,
}: {
  active: boolean;
  children: React.ReactNode;
  icon: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      className={`inline-flex min-h-10 items-center gap-2 rounded-md border px-3 text-sm font-semibold ${
        active ? "border-spruce bg-mist text-ink" : "border-slate-200 bg-white text-slate-600 hover:border-slate-300"
      }`}
      onClick={onClick}
      type="button"
    >
      {icon}
      {children}
    </button>
  );
}

function SegmentButton({
  active,
  children,
  onClick,
}: {
  active: boolean;
  children: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      className={`min-h-8 rounded px-3 text-sm font-semibold ${
        active ? "bg-spruce text-white" : "text-slate-600 hover:bg-mist"
      }`}
      onClick={onClick}
      type="button"
    >
      {children}
    </button>
  );
}

function HouseholdRollupSummary({
  client,
  output,
  grouping,
}: {
  client: HouseholdDetail;
  output: PortfolioRun | null;
  grouping: "account" | "goal";
}) {
  const rollups =
    grouping === "account"
      ? output?.output.account_rollups ?? []
      : output?.output.goal_rollups ?? [];
  const fallbackItems = grouping === "account" ? client.accounts : client.goals;
  return (
    <section className="rounded-md border border-slate-200 bg-white shadow-soft">
      <PanelTitle icon={<Activity size={17} />} title={grouping === "account" ? "Account Rollups" : "Goal Rollups"} />
      <div className="divide-y divide-slate-100">
        {rollups.length
          ? rollups.map((rollup) => (
              <div className="px-4 py-3" key={rollup.id}>
                <div className="mb-2 flex items-center justify-between gap-3">
                  <div className="font-semibold">{rollup.name}</div>
                  <div className="text-sm text-slate-600">{formatCurrency(rollup.allocated_amount)}</div>
                </div>
                <AllocationBars allocations={rollup.allocations} compact />
              </div>
            ))
          : fallbackItems.map((item) => (
              <div className="flex items-center justify-between gap-3 px-4 py-3" key={item.id}>
                <div className="font-semibold">{"type" in item ? item.type : item.name}</div>
                <div className="text-sm text-slate-600">
                  {"current_value" in item ? formatCurrency(item.current_value) : formatCurrency(item.current_funded_amount)}
                </div>
              </div>
            ))}
      </div>
    </section>
  );
}

function AccountConsole({
  account,
  accounts,
  goals,
  output,
  onSelectAccount,
}: {
  account: Account;
  accounts: Account[];
  goals: Goal[];
  output: PortfolioRun | null;
  onSelectAccount: (id: string) => void;
}) {
  const recommendations = recommendationsForAccount(output, account.id);
  const rollup = output?.output.account_rollups.find((item) => item.id === account.id);
  const fundedGoals = goals.filter((goal) =>
    goal.account_allocations.some((link) => link.account_id === account.id),
  );
  const currentAllocations = account.holdings.map((holding) => ({
    sleeve_id: holding.sleeve_id,
    sleeve_name: holding.sleeve_name,
    weight: Number(holding.weight),
  }));
  return (
    <div className="grid grid-cols-[300px_1fr] gap-5 max-lg:grid-cols-1">
      <EntityPicker
        items={accounts.map((item) => ({
          id: item.id,
          label: item.type,
          sublabel: formatCurrency(item.current_value),
        }))}
        selectedId={account.id}
        title="Accounts"
        onSelect={onSelectAccount}
      />
      <section className="rounded-md border border-slate-200 bg-white shadow-soft">
        <PanelTitle icon={<WalletCards size={17} />} title={`${account.type} Account`} />
        <div className="space-y-5 p-4">
          <div className="grid grid-cols-4 gap-3 max-xl:grid-cols-2 max-sm:grid-cols-1">
            <Metric label="Value" value={formatCurrency(account.current_value)} />
            <Metric label="Risk" value={account.regulatory_risk_rating} />
            <Metric label="Horizon" value={account.regulatory_time_horizon} />
            <Metric label="Cash State" value={account.cash_state.replace(/_/g, " ")} />
          </div>
          <div className="grid grid-cols-2 gap-5 max-xl:grid-cols-1">
            <AllocationSection title="Current" allocations={currentAllocations} emptyLabel="No holdings" />
            <AllocationSection title="Recommended" allocations={rollup?.allocations ?? []} emptyLabel="No run" />
          </div>
          <div>
            <h3 className="mb-2 text-sm font-bold uppercase tracking-wider text-slate-500">
              Funded Goals
            </h3>
            <div className="grid grid-cols-2 gap-3 max-md:grid-cols-1">
              {fundedGoals.map((goal) => (
                <div className="rounded-md border border-slate-100 px-3 py-3" key={goal.id}>
                  <div className="font-semibold">{goal.name}</div>
                  <div className="mt-1 text-sm text-slate-500">Risk {goal.goal_risk_score}/5</div>
                </div>
              ))}
            </div>
          </div>
          <RecommendationList recommendations={recommendations} />
        </div>
      </section>
    </div>
  );
}

function GoalConsole({
  accounts,
  goal,
  goals,
  output,
  onSelectGoal,
}: {
  accounts: Account[];
  goal: Goal;
  goals: Goal[];
  output: PortfolioRun | null;
  onSelectGoal: (id: string) => void;
}) {
  const [view, setView] = useState<"blended" | "legs">("blended");
  const recommendations = recommendationsForGoal(output, goal.id);
  const rollup = output?.output.goal_rollups.find((item) => item.id === goal.id);
  return (
    <div className="grid grid-cols-[300px_1fr] gap-5 max-lg:grid-cols-1">
      <EntityPicker
        items={goals.map((item) => ({
          id: item.id,
          label: item.name,
          sublabel: `${formatCurrency(item.current_funded_amount)} · risk ${item.goal_risk_score}/5`,
        }))}
        selectedId={goal.id}
        title="Goals"
        onSelect={onSelectGoal}
      />
      <section className="rounded-md border border-slate-200 bg-white shadow-soft">
        <PanelTitle icon={<Target size={17} />} title={goal.name} />
        <div className="space-y-5 p-4">
          <div className="grid grid-cols-4 gap-3 max-xl:grid-cols-2 max-sm:grid-cols-1">
            <Metric label="Target" value={goal.target_amount ? formatCurrency(goal.target_amount) : "No target"} />
            <Metric label="Funded" value={formatCurrency(goal.current_funded_amount)} />
            <Metric label="Risk" value={`${goal.goal_risk_score}/5`} />
            <Metric label="Date" value={goal.target_date} />
          </div>
          <div className="inline-flex rounded-md border border-slate-200 bg-white p-1">
            <SegmentButton active={view === "blended"} onClick={() => setView("blended")}>
              Blended
            </SegmentButton>
            <SegmentButton active={view === "legs"} onClick={() => setView("legs")}>
              By Account
            </SegmentButton>
          </div>
          {view === "blended" ? (
            <AllocationSection title="Blended Recommendation" allocations={rollup?.allocations ?? []} emptyLabel="No run" />
          ) : (
            <div className="space-y-3">
              {recommendations.map((recommendation) => {
                const account = accounts.find((item) => item.id === recommendation.account_id);
                return (
                  <div className="rounded-md border border-slate-100 px-3 py-3" key={recommendation.link_id}>
                    <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <div className="font-semibold">{account?.type ?? recommendation.account_type}</div>
                        <div className="text-sm text-slate-500">
                          {formatCurrency(recommendation.allocated_amount)} · p{recommendation.frontier_percentile}
                        </div>
                      </div>
                      <span className="rounded-full bg-mist px-2 py-1 text-xs font-bold">
                        Risk {recommendation.goal_risk_score}/5
                      </span>
                    </div>
                    <AllocationBars allocations={recommendation.allocations} compact />
                    <DiagnosticsBanner recommendation={recommendation} />
                  </div>
                );
              })}
            </div>
          )}
          <RecommendationList recommendations={recommendations} />
        </div>
      </section>
    </div>
  );
}

function EntityPicker({
  items,
  selectedId,
  title,
  onSelect,
}: {
  items: Array<{ id: string; label: string; sublabel: string }>;
  selectedId: string;
  title: string;
  onSelect: (id: string) => void;
}) {
  return (
    <aside className="rounded-md border border-slate-200 bg-white shadow-soft">
      <PanelTitle icon={<Database size={17} />} title={title} />
      <div className="divide-y divide-slate-100">
        {items.map((item) => (
          <button
            className={`w-full px-4 py-3 text-left ${
              selectedId === item.id ? "bg-mist" : "bg-white hover:bg-[#fbfaf5]"
            }`}
            key={item.id}
            onClick={() => onSelect(item.id)}
            type="button"
          >
            <div className="font-semibold">{item.label}</div>
            <div className="mt-1 text-sm text-slate-500">{item.sublabel}</div>
          </button>
        ))}
      </div>
    </aside>
  );
}

function AllocationSection({
  allocations,
  emptyLabel,
  title,
}: {
  allocations: Allocation[];
  emptyLabel: string;
  title: string;
}) {
  return (
    <div>
      <h3 className="mb-2 text-sm font-bold uppercase tracking-wider text-slate-500">{title}</h3>
      {allocations.length ? (
        <AllocationBars allocations={allocations} />
      ) : (
        <div className="rounded-md bg-mist px-3 py-3 text-sm text-slate-600">{emptyLabel}</div>
      )}
    </div>
  );
}

function RecommendationList({ recommendations }: { recommendations: LinkRecommendation[] }) {
  if (!recommendations.length) {
    return null;
  }
  return (
    <div>
      <h3 className="mb-2 text-sm font-bold uppercase tracking-wider text-slate-500">
        Recommendations
      </h3>
      <div className="space-y-3">
        {recommendations.map((recommendation) => (
          <RecommendationCard key={recommendation.link_id} recommendation={recommendation} />
        ))}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white px-4 py-3 shadow-soft">
      <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
    </div>
  );
}

function PeoplePanel({ client }: { client: HouseholdDetail }) {
  return (
    <section className="rounded-md border border-slate-200 bg-white shadow-soft">
      <PanelTitle icon={<ShieldCheck size={17} />} title="Household Members" />
      <div className="grid grid-cols-2 gap-3 p-4 max-md:grid-cols-1">
        {client.members.map((person) => (
          <div className="rounded-md bg-mist px-3 py-3" key={person.id}>
            <div className="font-semibold">{person.name}</div>
            <div className="mt-1 text-sm text-slate-600">
              {person.investment_knowledge} knowledge · {person.marital_status}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function GoalsPanel({ goals }: { goals: Goal[] }) {
  return (
    <section className="rounded-md border border-slate-200 bg-white shadow-soft">
      <PanelTitle icon={<Activity size={17} />} title="Goals" />
      <div className="divide-y divide-slate-100">
        {goals.map((goal) => (
          <div className="grid grid-cols-[1fr_auto] gap-4 px-4 py-3 max-sm:grid-cols-1" key={goal.id}>
            <div>
              <div className="font-semibold">{goal.name}</div>
              <div className="mt-1 text-sm text-slate-600">{goal.notes}</div>
              <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-500">
                {goal.account_allocations.length ? (
                  goal.account_allocations.map((link) => (
                    <span className="rounded-full bg-mist px-2 py-1" key={`${link.goal_id}-${link.account_id}`}>
                      Account link {link.account_id}
                      {link.allocated_amount ? ` · ${formatCurrency(link.allocated_amount)}` : ""}
                    </span>
                  ))
                ) : (
                  <span className="rounded-full bg-slate-100 px-2 py-1">No account mapping</span>
                )}
              </div>
            </div>
            <div className="text-right max-sm:text-left">
              <div className="font-semibold">{goal.target_amount ? formatCurrency(goal.target_amount) : "No target"}</div>
              <div className="mt-1 text-xs uppercase tracking-wider text-slate-500">
                {goal.target_date} · necessity {goal.necessity_score}/5
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function AccountsPanel({ accounts }: { accounts: Account[] }) {
  return (
    <section className="rounded-md border border-slate-200 bg-white shadow-soft">
      <PanelTitle icon={<Database size={17} />} title="Accounts" />
      <div className="divide-y divide-slate-100">
        {accounts.map((account) => (
          <div className="px-4 py-3" key={account.id}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="font-semibold">{account.type}</div>
                <div className="mt-1 text-xs uppercase tracking-wider text-slate-500">
                  {account.regulatory_objective} · {account.regulatory_time_horizon}
                </div>
              </div>
              <div className="text-right">
                <div className="font-semibold">{formatCurrency(account.current_value)}</div>
                <RiskBadge rating={account.regulatory_risk_rating} />
              </div>
            </div>
            <div className="mt-3 grid grid-cols-3 gap-2 max-md:grid-cols-1">
              {account.holdings.length ? account.holdings.map((holding) => (
                <div className="rounded-md bg-[#fbfaf5] px-3 py-2 text-sm" key={holding.sleeve_id}>
                  <div className="font-medium">{holding.sleeve_name}</div>
                  <div className="text-slate-500">{formatPercent(holding.weight)}</div>
                </div>
              )) : <div className="rounded-md bg-[#fbfaf5] px-3 py-2 text-sm text-slate-500">Holdings not available</div>}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function PortfolioPanel({
  client,
  output,
  runHistory,
}: {
  client: HouseholdDetail;
  output: PortfolioRun | null;
  runHistory: HouseholdDetail["portfolio_runs"];
}) {
  const [auditOpen, setAuditOpen] = useState(false);
  const [auditExport, setAuditExport] = useState<PortfolioAuditExport | null>(null);
  const queryClient = useQueryClient();
  const declineMutation = useMutation({
    mutationFn: () => (output ? declinePortfolioRun(client.id, output.external_id) : Promise.reject()),
    onSuccess: (run) => {
      setAuditExport(null);
      void queryClient.invalidateQueries({ queryKey: ["client", client.id] });
      queryClient.setQueryData(["client", client.id], (previous: HouseholdDetail | undefined) =>
        previous ? { ...previous, latest_portfolio_run: run } : previous,
      );
    },
  });
  const exportMutation = useMutation({
    mutationFn: () => (output ? exportPortfolioAudit(client.id, output.external_id) : Promise.reject()),
    onSuccess: (payload) => {
      setAuditExport(payload);
      setAuditOpen(true);
    },
  });
  if (!output) {
    return (
      <section className="rounded-md border border-slate-200 bg-white p-5 shadow-soft">
        <PanelTitle icon={<BarChart3 size={17} />} title="Portfolio Output" />
        <div className="mt-8 rounded-md bg-skyglass px-4 py-5 text-sm text-slate-700">
          Generate the portfolio to create a link-level recommendation run.
        </div>
      </section>
    );
  }

  const engineOutput = output.output;
  const history = [
    output,
    ...runHistory.filter((run) => run.external_id !== output.external_id),
  ].slice(0, 5);
  const hasHashWarning = output.status === "hash_mismatch";
  return (
    <section className="rounded-md border border-slate-200 bg-white shadow-soft">
      <PanelTitle icon={<BarChart3 size={17} />} title="Portfolio Output" />
      <div className="space-y-5 p-4">
        <div className="rounded-md bg-mist px-4 py-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Latest Run
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-slate-700">
            <span className="font-semibold">{output.status}</span>
            <span>CMA {engineOutput.audit_trace.cma_version}</span>
            <span>{new Date(output.created_at).toLocaleString()}</span>
            {hasHashWarning ? <span className="rounded-full bg-[#ffe0d2] px-2 py-1 text-xs font-bold text-[#7d3b20]">Hash warning</span> : null}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => exportMutation.mutate()} disabled={exportMutation.isPending}>
            <Download size={16} />
            {exportMutation.isPending ? "Exporting" : "Audit"}
          </Button>
          <Button onClick={() => declineMutation.mutate()} disabled={declineMutation.isPending || output.status === "declined"}>
            <X size={16} />
            {declineMutation.isPending ? "Declining" : "Decline"}
          </Button>
        </div>
        {exportMutation.error ? (
          <div className="rounded-md bg-[#ffe0d2] px-3 py-2 text-sm text-[#7d3b20]">
            {exportMutation.error.message}
          </div>
        ) : null}

        <div>
          <h3 className="mb-2 text-sm font-bold uppercase tracking-wider text-slate-500">
            Household Blend
          </h3>
          <AllocationBars allocations={engineOutput.household_rollup.allocations} />
        </div>

        <div>
          <h3 className="mb-2 text-sm font-bold uppercase tracking-wider text-slate-500">
            Goal-Account Recommendations
          </h3>
          <div className="space-y-3">
            {engineOutput.link_recommendations.map((recommendation) => (
              <RecommendationCard key={recommendation.link_id} recommendation={recommendation} />
            ))}
          </div>
        </div>

        <div>
          <h3 className="mb-2 text-sm font-bold uppercase tracking-wider text-slate-500">
            Run History
          </h3>
          <div className="divide-y divide-slate-100 rounded-md border border-slate-100">
            {history.map((run) => (
              <div
                className="flex flex-wrap items-center justify-between gap-3 px-3 py-2 text-sm"
                key={run.external_id}
              >
                <div>
                  <span className="font-semibold">{run.status}</span>
                  <span className="ml-2 text-slate-500">
                    {new Date(run.created_at).toLocaleString()}
                  </span>
                </div>
                <div className="text-xs text-slate-500">{run.engine_version}</div>
              </div>
            ))}
          </div>
        </div>

        <details className="rounded-md bg-[#fbfaf5] px-4 py-3 text-sm text-slate-700">
          <summary className="cursor-pointer font-semibold">Why this recommendation?</summary>
          <p className="mt-2">{output.advisor_summary}</p>
          <div className="mt-3 grid gap-2 text-xs text-slate-500">
            <span>Engine {output.engine_version}</span>
            <span>Input hash {output.input_hash.slice(0, 12)}</span>
            <span>Output hash {output.output_hash.slice(0, 12)}</span>
            <span>CMA hash {output.cma_hash.slice(0, 12)}</span>
          </div>
        </details>
      </div>
      {auditOpen ? (
        <AuditDrawer
          exportPayload={auditExport}
          isLoading={exportMutation.isPending}
          output={output}
          onClose={() => setAuditOpen(false)}
          onExport={() => exportMutation.mutate()}
        />
      ) : null}
    </section>
  );
}

function RecommendationCard({ recommendation }: { recommendation: LinkRecommendation }) {
  return (
    <div className="rounded-md border border-slate-100 p-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="font-semibold">{recommendation.goal_name}</div>
          <div className="text-xs text-slate-500">
            {recommendation.account_type} · {formatCurrency(recommendation.allocated_amount)}
          </div>
        </div>
        <span className="rounded-full bg-mist px-2 py-1 text-xs font-bold">
          p{recommendation.frontier_percentile}
        </span>
      </div>
      <div className="mt-2 text-xs text-slate-500">
        Return {percent.format(recommendation.expected_return)} · Volatility{" "}
        {percent.format(recommendation.volatility)} · Horizon{" "}
        {recommendation.horizon_years.toFixed(1)} years · Risk {recommendation.goal_risk_score}/5
      </div>
      <div className="mt-3">
        <AllocationBars allocations={recommendation.allocations} compact />
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {recommendation.allocations.map((allocation) => (
          <span className="rounded-full bg-[#fbfaf5] px-2 py-1 text-xs text-slate-600" key={`${recommendation.link_id}-${allocation.sleeve_id}`}>
            {allocation.fund_type === "whole_portfolio" ? "Whole" : "Block"} · {allocation.sleeve_name}
          </span>
        ))}
      </div>
      <DiagnosticsBanner recommendation={recommendation} />
    </div>
  );
}

function DiagnosticsBanner({ recommendation }: { recommendation: LinkRecommendation }) {
  const comparison = recommendation.current_comparison;
  const warnings = new Set([...(recommendation.warnings ?? []), ...(comparison.warnings ?? [])]);
  if (!warnings.size && comparison.status === "mapped") {
    return (
      <div className="mt-3 flex items-center gap-2 rounded-md bg-mist px-3 py-2 text-xs text-spruce">
        <CheckCircle2 size={14} />
        Current holdings mapped to the active fund universe.
      </div>
    );
  }
  return (
    <div className="mt-3 rounded-md bg-[#fff1c7] px-3 py-2 text-xs text-[#775b0b]">
      <div className="font-semibold">{comparison.reason || "Diagnostics available."}</div>
      {warnings.size ? <div className="mt-1">{Array.from(warnings).join(" · ")}</div> : null}
    </div>
  );
}

function AuditDrawer({
  exportPayload,
  isLoading,
  output,
  onClose,
  onExport,
}: {
  exportPayload: PortfolioAuditExport | null;
  isLoading: boolean;
  output: PortfolioRun;
  onClose: () => void;
  onExport: () => void;
}) {
  const verificationOk = exportPayload?.verification.ok ?? output.status !== "hash_mismatch";
  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/25">
      <aside className="h-full w-full max-w-xl overflow-y-auto bg-white shadow-soft">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <div>
            <h2 className="text-lg font-semibold">Audit</h2>
            <div className="mt-1 flex items-center gap-2 text-sm text-slate-600">
              {verificationOk ? <CheckCircle2 size={15} className="text-spruce" /> : <X size={15} className="text-[#7d3b20]" />}
              {verificationOk ? "Verified" : "Warning"}
            </div>
          </div>
          <button
            aria-label="Close audit"
            className="flex h-9 w-9 items-center justify-center rounded-md border border-slate-200"
            onClick={onClose}
            type="button"
          >
            <X size={16} />
          </button>
        </div>
        <div className="space-y-5 p-5">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <HashValue label="Input" value={output.input_hash} />
            <HashValue label="Output" value={output.output_hash} />
            <HashValue label="CMA" value={output.cma_hash} />
            <HashValue label="Signature" value={output.run_signature} />
          </div>
          <Button disabled={isLoading} onClick={onExport}>
            <Download size={16} />
            {isLoading ? "Exporting" : "Refresh Export"}
          </Button>
          {exportPayload ? (
            <>
              <div>
                <h3 className="mb-2 text-sm font-bold uppercase tracking-wider text-slate-500">
                  Diagnostics
                </h3>
                <pre className="max-h-72 overflow-auto rounded-md bg-[#fbfaf5] p-3 text-xs text-slate-700">
                  {JSON.stringify(exportPayload.diagnostics, null, 2)}
                </pre>
              </div>
              <div>
                <h3 className="mb-2 text-sm font-bold uppercase tracking-wider text-slate-500">
                  Events
                </h3>
                <div className="space-y-2">
                  {exportPayload.lifecycle_events.map((event, index) => (
                    <div className="rounded-md border border-slate-100 px-3 py-2 text-sm" key={`${event.event_type}-${index}`}>
                      <div className="font-semibold">{event.event_type}</div>
                      <div className="text-xs text-slate-500">{new Date(event.created_at).toLocaleString()}</div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="rounded-md bg-mist px-3 py-3 text-sm text-slate-600">
              Export the audit bundle to view diagnostics and lifecycle events.
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}

function HashValue({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-mist px-3 py-2">
      <div className="text-xs font-bold uppercase tracking-wider text-slate-500">{label}</div>
      <div className="mt-1 font-mono text-xs">{value.slice(0, 16)}</div>
    </div>
  );
}

function recommendationsForAccount(output: PortfolioRun | null, accountId: string): LinkRecommendation[] {
  return (output?.output.link_recommendations ?? []).filter(
    (recommendation) => recommendation.account_id === accountId,
  );
}

function recommendationsForGoal(output: PortfolioRun | null, goalId: string): LinkRecommendation[] {
  return (output?.output.link_recommendations ?? []).filter(
    (recommendation) => recommendation.goal_id === goalId,
  );
}

function AllocationBars({ allocations, compact = false }: { allocations: Allocation[]; compact?: boolean }) {
  const palette = ["bg-spruce", "bg-copper", "bg-citrine", "bg-[#5b7f95]", "bg-[#8f6f9f]", "bg-[#7a8b42]"];
  return (
    <div className="space-y-2">
      {allocations.map((allocation, index) => (
        <div className="grid grid-cols-[minmax(130px,1fr)_2.2fr_54px] items-center gap-3" key={allocation.sleeve_id}>
          <div className={`${compact ? "text-xs" : "text-sm"} font-medium`}>{allocation.sleeve_name}</div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-100">
            <div
              className={`h-full ${palette[index % palette.length]}`}
              style={{ width: `${Math.max(allocation.weight * 100, 2)}%` }}
            />
          </div>
          <div className="text-right text-xs font-semibold text-slate-600">
            {percent.format(allocation.weight)}
          </div>
        </div>
      ))}
    </div>
  );
}

function RiskBadge({ rating }: { rating: string }) {
  const color =
    rating === "low"
      ? "bg-skyglass text-[#31556a]"
      : rating === "medium"
        ? "bg-[#fff1c7] text-[#775b0b]"
        : "bg-[#ffe0d2] text-[#7d3b20]";
  return (
    <span className={`inline-flex rounded-full px-2 py-1 text-xs font-bold uppercase ${color}`}>
      {rating}
    </span>
  );
}

function PanelTitle({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <div className="flex items-center gap-2 border-b border-slate-100 px-4 py-3">
      <span className="text-spruce">{icon}</span>
      <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">{title}</h3>
    </div>
  );
}

function EmptyState({ label }: { label: string }) {
  return (
    <div className="flex min-h-[60vh] items-center justify-center rounded-md border border-slate-200 bg-white text-slate-500">
      {label}
    </div>
  );
}

function formatCurrency(value: unknown): string {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? currency.format(numeric) : "Not available";
}

function formatPercent(value: unknown): string {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? percent.format(numeric) : "Not available";
}

export default App;
