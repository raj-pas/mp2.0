import { cn } from "../lib/cn";

export type GroupByMode = "by-account" | "by-goal";

interface ModeToggleProps {
  label: string;
  options: { value: GroupByMode; label: string }[];
  value: GroupByMode;
  onChange: (value: GroupByMode) => void;
}

export function ModeToggle({ label, options, value, onChange }: ModeToggleProps) {
  return (
    <div className="flex items-center gap-2" role="group" aria-label={label}>
      <span className="font-mono text-[9px] uppercase tracking-widest text-muted">{label}</span>
      <div className="inline-flex border border-hairline bg-paper-2 p-0.5">
        {options.map((opt) => {
          const on = opt.value === value;
          return (
            <button
              key={opt.value}
              type="button"
              data-on={on}
              aria-pressed={on}
              onClick={() => onChange(opt.value)}
              className={cn(
                "px-2.5 py-1 font-sans text-[11px] font-medium transition-colors",
                on ? "bg-ink text-paper" : "text-muted hover:text-ink",
              )}
            >
              {opt.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
