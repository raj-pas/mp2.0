import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  ArrowRight,
  BarChart3,
  Database,
  FileText,
  LogIn,
  LogOut,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import { useMemo, useState } from "react";

import { fetchClient, fetchClients, fetchSession, generatePortfolio, login, logout } from "./api";
import { Button } from "./components/ui/button";
import { ReviewShell } from "./ReviewShell";
import type { Account, EngineOutput, Goal, HouseholdDetail, HouseholdSummary } from "./types";

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
  const [mode, setMode] = useState<"clients" | "review">("clients");
  const queryClient = useQueryClient();
  const session = useQuery({
    queryKey: ["session"],
    queryFn: fetchSession,
  });
  const isAuthenticated = Boolean(session.data?.authenticated);
  const clients = useQuery({
    queryKey: ["clients"],
    queryFn: fetchClients,
    enabled: isAuthenticated,
  });
  const selectedClient = useQuery({
    queryKey: ["client", selectedClientId],
    queryFn: () => fetchClient(selectedClientId),
    enabled: Boolean(selectedClientId) && isAuthenticated,
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
    if (portfolioMutation.data) {
      return portfolioMutation.data;
    }
    const saved = selectedClient.data?.last_engine_output;
    return saved && "goal_blends" in saved ? (saved as EngineOutput) : null;
  }, [portfolioMutation.data, selectedClient.data?.last_engine_output]);

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
          <div className="mb-5 grid grid-cols-2 gap-2">
            <ModeButton active={mode === "clients"} icon={<Database size={15} />} onClick={() => setMode("clients")}>
              Clients
            </ModeButton>
            <ModeButton active={mode === "review"} icon={<FileText size={15} />} onClick={() => setMode("review")}>
              Review
            </ModeButton>
          </div>
          <SessionStatus
            authenticated={Boolean(session.data?.authenticated)}
            email={session.data?.user?.email}
            isLoading={session.isLoading}
            isLoggingOut={logoutMutation.isPending}
            onLogout={() => logoutMutation.mutate()}
          />
          <ClientList
            authenticated={isAuthenticated}
            clients={isAuthenticated ? (clients.data ?? []) : []}
            isLoading={isAuthenticated && clients.isLoading}
            selectedClientId={selectedClientId}
            onSelect={setSelectedClientId}
          />
        </aside>

        <section className="min-w-0 px-6 py-5">
          {mode === "review" ? (
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
  output: EngineOutput | null;
  error?: string;
  isGenerating: boolean;
  onGenerate: () => void;
}) {
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
        <Metric label="Household Risk" value={`${client.household_risk_score}/10`} />
        <Metric label="Goals" value={String(client.goals.length)} />
        <Metric label="Accounts" value={String(client.accounts.length)} />
      </div>

      <div className="grid grid-cols-[1.1fr_0.9fr] gap-5 max-xl:grid-cols-1">
        <div className="space-y-5">
          <PeoplePanel client={client} />
          <GoalsPanel goals={client.goals} />
          <AccountsPanel accounts={client.accounts} />
        </div>
        <PortfolioPanel output={output} />
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
              <div className="font-semibold">{formatCurrency(goal.target_amount)}</div>
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

function PortfolioPanel({ output }: { output: EngineOutput | null }) {
  if (!output) {
    return (
      <section className="rounded-md border border-slate-200 bg-white p-5 shadow-soft">
        <PanelTitle icon={<BarChart3 size={17} />} title="Portfolio Output" />
        <div className="mt-8 rounded-md bg-skyglass px-4 py-5 text-sm text-slate-700">
          Generate the portfolio to call the Phase 1 engine stub and write an audit event.
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white shadow-soft">
      <PanelTitle icon={<BarChart3 size={17} />} title="Portfolio Output" />
      <div className="space-y-5 p-4">
        <div className="rounded-md bg-mist px-4 py-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Household Risk Rating
          </div>
          <div className="mt-1 flex items-center gap-2 text-2xl font-semibold">
            {output.household_risk_rating}
            <RiskBadge rating={output.household_risk_rating} />
          </div>
        </div>

        <div>
          <h3 className="mb-2 text-sm font-bold uppercase tracking-wider text-slate-500">
            Household Blend
          </h3>
          <AllocationBars allocations={output.household_blend} />
        </div>

        <div>
          <h3 className="mb-2 text-sm font-bold uppercase tracking-wider text-slate-500">
            Goal Blends
          </h3>
          <div className="space-y-3">
            {output.goal_blends.map((blend) => (
              <div className="rounded-md border border-slate-100 p-3" key={blend.goal_id}>
                <div className="flex items-center justify-between gap-3">
                  <div className="font-semibold">{blend.goal_name}</div>
                  <RiskBadge rating={blend.risk_rating} />
                </div>
                <div className="mt-2 text-xs text-slate-500">
                  Return {percent.format(blend.expected_return)} · Volatility{" "}
                  {percent.format(blend.volatility)} · Frontier p{blend.frontier_percentile}
                </div>
                <div className="mt-3">
                  <AllocationBars allocations={blend.allocations} compact />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-md bg-[#fbfaf5] px-4 py-3 text-sm text-slate-700">
          {output.narrative_summary}
        </div>
      </div>
    </section>
  );
}

function AllocationBars({ allocations, compact = false }: { allocations: EngineOutput["household_blend"]; compact?: boolean }) {
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
