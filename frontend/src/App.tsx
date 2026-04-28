import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, ArrowRight, BarChart3, Database, RefreshCw, ShieldCheck } from "lucide-react";
import { useMemo, useState } from "react";

import { fetchClient, fetchClients, generatePortfolio } from "./api";
import { Button } from "./components/ui/button";
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
  const queryClient = useQueryClient();
  const clients = useQuery({
    queryKey: ["clients"],
    queryFn: fetchClients,
  });
  const selectedClient = useQuery({
    queryKey: ["client", selectedClientId],
    queryFn: () => fetchClient(selectedClientId),
    enabled: Boolean(selectedClientId),
  });
  const portfolioMutation = useMutation({
    mutationFn: () => generatePortfolio(selectedClientId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["client", selectedClientId] });
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
              <p className="text-xs text-slate-500">Phase 1 local scaffold</p>
            </div>
          </div>
          <ClientList
            clients={clients.data ?? []}
            isLoading={clients.isLoading}
            selectedClientId={selectedClientId}
            onSelect={setSelectedClientId}
          />
        </aside>

        <section className="min-w-0 px-6 py-5">
          {selectedClient.isLoading ? (
            <EmptyState label="Loading client" />
          ) : selectedClient.error ? (
            <EmptyState label="Backend unavailable" />
          ) : selectedClient.data ? (
            <AdvisorWorkspace
              client={selectedClient.data}
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

function ClientList({
  clients,
  isLoading,
  selectedClientId,
  onSelect,
}: {
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
        {isLoading ? (
          <div className="rounded-md bg-mist px-3 py-3 text-sm text-slate-600">Loading</div>
        ) : (
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
                <span>{currency.format(client.total_assets)}</span>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}

function AdvisorWorkspace({
  client,
  output,
  isGenerating,
  onGenerate,
}: {
  client: HouseholdDetail;
  output: EngineOutput | null;
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

      <div className="grid grid-cols-4 gap-3 max-xl:grid-cols-2 max-sm:grid-cols-1">
        <Metric label="Total Assets" value={currency.format(client.total_assets)} />
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
            </div>
            <div className="text-right max-sm:text-left">
              <div className="font-semibold">{currency.format(Number(goal.target_amount))}</div>
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
                <div className="font-semibold">{currency.format(Number(account.current_value))}</div>
                <RiskBadge rating={account.regulatory_risk_rating} />
              </div>
            </div>
            <div className="mt-3 grid grid-cols-3 gap-2 max-md:grid-cols-1">
              {account.holdings.map((holding) => (
                <div className="rounded-md bg-[#fbfaf5] px-3 py-2 text-sm" key={holding.sleeve_id}>
                  <div className="font-medium">{holding.sleeve_name}</div>
                  <div className="text-slate-500">{percent.format(Number(holding.weight))}</div>
                </div>
              ))}
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

export default App;
