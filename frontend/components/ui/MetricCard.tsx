import type { ReactNode } from "react";

export function MetricCard({
  label,
  value,
  hint,
  icon,
  unavailable,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  icon?: ReactNode;
  unavailable?: boolean;
}) {
  return (
    <div className="rounded-2xl border border-white/[0.06] bg-card p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-[11px] uppercase tracking-[0.14em] text-mist">{label}</p>
        {icon ? <span className="text-mist/70">{icon}</span> : null}
      </div>
      <p
        className={`mt-2 font-mono text-2xl font-semibold tabular-nums ${
          unavailable ? "text-mist" : "text-[#F5F7FA]"
        }`}
      >
        {value}
      </p>
      {hint ? <p className="mt-1 text-[11px] text-mist">{hint}</p> : null}
    </div>
  );
}
