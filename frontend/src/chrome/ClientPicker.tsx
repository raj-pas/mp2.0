import * as Popover from "@radix-ui/react-popover";
import { ChevronDown, Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { Skeleton } from "../components/ui/skeleton";
import { useClients, type ClientSummary } from "../lib/clients";
import { useLocalStorage } from "../lib/local-storage";
import { formatCadCompact } from "../lib/format";
import { cn } from "../lib/cn";

interface ClientPickerProps {
  selectedId: string | null;
  onSelect: (id: string) => void;
  enabled?: boolean;
}

export function ClientPicker({ selectedId, onSelect, enabled = true }: ClientPickerProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const clients = useClients(enabled);

  const filtered = useMemo<ClientSummary[]>(() => {
    if (!clients.data) return [];
    const q = query.trim().toLowerCase();
    if (q.length === 0) return clients.data;
    return clients.data.filter((c) => c.display_name.toLowerCase().includes(q));
  }, [clients.data, query]);

  const selected =
    selectedId !== null ? (clients.data?.find((c) => c.id === selectedId) ?? null) : null;

  function handleSelect(id: string) {
    setOpen(false);
    setQuery("");
    onSelect(id);
  }

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          type="button"
          className={cn(
            "flex items-center gap-2 border border-hairline-2 bg-paper-2 px-3 py-1 text-left transition-colors",
            "hover:border-ink/40",
            "data-[state=open]:border-ink/40 data-[state=open]:bg-paper",
          )}
          aria-label={t("topbar.client_picker_label")}
        >
          <span className="font-sans text-[12px] font-semibold text-ink">
            {selected?.display_name ?? t("topbar.client_picker_placeholder")}
          </span>
          {selected?.total_assets != null && (
            <span className="font-serif text-[14px] font-medium text-accent-2">
              {formatCadCompact(selected.total_assets)}
            </span>
          )}
          <ChevronDown aria-hidden className="h-3 w-3 text-muted-2" />
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          align="start"
          sideOffset={6}
          className="z-50 w-80 border border-hairline-2 bg-paper shadow-md"
        >
          <div className="border-b border-hairline p-2">
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t("topbar.client_picker_search")}
              className="w-full border border-hairline bg-paper-2 px-2 py-1 font-sans text-[12px] text-ink focus:border-accent focus:outline-none"
              aria-label={t("topbar.client_picker_search")}
            />
          </div>
          <div className="max-h-72 overflow-y-auto" role="listbox">
            {clients.isPending && <ClientPickerSkeleton />}
            {clients.isError && (
              <p className="p-3 font-mono text-[10px] uppercase tracking-widest text-danger">
                {t("topbar.client_picker_error")}
              </p>
            )}
            {clients.isSuccess && filtered.length === 0 && (
              <p className="p-3 font-mono text-[10px] uppercase tracking-widest text-muted">
                {query.length > 0 ? t("topbar.client_picker_no_match") : t("empty.no_clients")}
              </p>
            )}
            <button
              type="button"
              onClick={() => {
                setOpen(false);
                navigate("/wizard/new");
              }}
              className="flex w-full items-center justify-between border-b border-hairline bg-paper-2 px-3 py-2 text-left transition-colors hover:bg-paper"
            >
              <span className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-ink">
                <Plus aria-hidden className="h-3 w-3" />
                {t("topbar.client_picker_add")}
              </span>
            </button>
            {filtered.map((client) => {
              const active = client.id === selectedId;
              return (
                <button
                  key={client.id}
                  type="button"
                  role="option"
                  aria-selected={active}
                  onClick={() => handleSelect(client.id)}
                  className={cn(
                    "flex w-full items-center justify-between border-b border-hairline px-3 py-2 text-left transition-colors last:border-b-0",
                    active ? "bg-paper-2" : "bg-paper hover:bg-paper-2",
                  )}
                >
                  <span className="font-sans text-[12px] font-medium text-ink">
                    {client.display_name}
                  </span>
                  {client.total_assets != null && (
                    <span className="font-mono text-[10px] text-accent-2">
                      {formatCadCompact(client.total_assets)}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}

function ClientPickerSkeleton() {
  return (
    <div className="flex flex-col gap-2 p-3">
      <Skeleton className="h-6 w-full" />
      <Skeleton className="h-6 w-3/4" />
      <Skeleton className="h-6 w-2/3" />
    </div>
  );
}

export const LAST_CLIENT_STORAGE_KEY = "mp20_last_client_id";

export function useRememberedClientId(): [string | null, (id: string | null) => void] {
  return useLocalStorage<string | null>(LAST_CLIENT_STORAGE_KEY, null);
}
