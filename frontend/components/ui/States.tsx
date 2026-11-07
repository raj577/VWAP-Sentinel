import Link from "next/link";
import type { ReactNode } from "react";

export function EmptyState({
  title,
  description,
  action,
  icon,
}: {
  title: string;
  description: string;
  action?: { href: string; label: string };
  icon?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-white/[0.08] bg-card/50 px-6 py-12 text-center">
      {icon ? <div className="mb-3 text-mist">{icon}</div> : null}
      <h3 className="text-sm font-semibold text-[#F5F7FA]">{title}</h3>
      <p className="mt-1 max-w-md text-xs leading-relaxed text-mist">{description}</p>
      {action ? (
        <Link
          href={action.href}
          className="mt-4 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-[#F5F7FA] hover:bg-white/5"
        >
          {action.label}
        </Link>
      ) : null}
    </div>
  );
}

export function ErrorState({
  title = "Could not load this data",
  message,
}: {
  title?: string;
  message: string;
}) {
  return (
    <div className="rounded-2xl border border-red-500/25 bg-red-500/[0.06] p-4 text-sm">
      <p className="font-medium text-red-200">{title}</p>
      <p className="mt-1 text-xs text-red-200/80">{message}</p>
    </div>
  );
}

export function IntegrationPlaceholder({
  title,
  description,
  endpoints,
}: {
  title: string;
  description: string;
  endpoints: string[];
}) {
  return (
    <div className="rounded-2xl border border-amber-400/20 bg-amber-400/[0.05] p-5">
      <p className="text-sm font-semibold text-amber-200">{title}</p>
      <p className="mt-1 text-xs leading-relaxed text-amber-200/80">{description}</p>
      <div className="mt-3">
        <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-amber-200/70">
          Required backend endpoints
        </p>
        <ul className="mt-1.5 space-y-1 font-mono text-[11px] text-amber-100/80">
          {endpoints.map((endpoint) => (
            <li key={endpoint}>{endpoint}</li>
          ))}
        </ul>
      </div>
      <p className="mt-3 text-[10px] text-amber-200/60">
        No placeholder data is shown for this module.
      </p>
    </div>
  );
}
