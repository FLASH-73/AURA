interface MetricCardProps {
  label: string;
  value: string;
  context?: string;
}

export function MetricCard({ label, value, context }: MetricCardProps) {
  return (
    <div className="flex flex-col items-center">
      <span className="text-[11px] font-medium uppercase tracking-[0.02em] text-text-tertiary">
        {label}
      </span>
      <span className="font-mono text-[32px] font-semibold leading-tight tabular-nums text-text-primary">
        {value}
      </span>
      {context && (
        <span className="font-mono text-[12px] text-text-tertiary">
          {context}
        </span>
      )}
    </div>
  );
}
