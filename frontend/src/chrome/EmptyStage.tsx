interface EmptyStageProps {
  phaseLabel?: string;
  title: string;
  description: string;
}

export function EmptyStage({ phaseLabel, title, description }: EmptyStageProps) {
  return (
    <main className="flex flex-1 flex-col items-center justify-center bg-paper p-12">
      <div className="max-w-2xl text-center">
        {phaseLabel !== undefined && phaseLabel.length > 0 && (
          <p className="mb-3 font-mono text-[10px] uppercase tracking-widest text-muted">
            {phaseLabel}
          </p>
        )}
        <h1 className="font-serif text-3xl font-medium tracking-tight text-ink">{title}</h1>
        <p className="mt-4 text-sm leading-relaxed text-muted">{description}</p>
      </div>
    </main>
  );
}
