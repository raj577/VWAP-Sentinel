"use client";

import { useEffect, useState } from "react";

import { formatCount, formatDateTime } from "@/lib/format";
import type { SchedulerStatus } from "@/types/api";

function statusClass(status: string): string {
  if (status === "COMPLETED") return "bg-emerald-500/10 text-emerald-300";
  if (status === "FAILED") return "bg-red-500/10 text-red-300";
  if (status === "CANCELLED") return "bg-white/5 text-muted";
  if (status === "PARTIALLY_COMPLETED") return "bg-amber-500/10 text-amber-300";
  return "bg-sky-500/10 text-sky-300";
}

export function SchedulerLivePanel({
  initial,
}: {
  initial: SchedulerStatus | null;
}) {
  const [status, setStatus] = useState<SchedulerStatus | null>(initial);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const response = await fetch("/api/admin/scheduler/status", {
          cache: "no-store",
        });
        if (!response.ok) return;
        const body = (await response.json()) as SchedulerStatus;
        if (!cancelled) setStatus(body);
      } catch {
        // keep the last known state
      }
    }

    void load();
    const timer = window.setInterval(() => void load(), 5000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  const active = status?.active_job ?? null;
  const percent =
    active && active.total_instruments > 0
      ? Math.min(
          100,
          Math.round(
            (active.processed_instruments / active.total_instruments) * 100,
          ),
        )
      : 0;

  return (
    <section className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-lg border border-border bg-panel p-4">
          <p className="text-xs uppercase tracking-wide text-muted">Scheduler</p>
          <p className="mt-2 text-lg font-semibold text-white">
            {status?.settings.scheduler_enabled ? "Enabled" : "Paused"}
          </p>
          <p className="mt-1 text-xs text-muted">
            every {status?.settings.scan_interval_minutes ?? "—"} min
          </p>
        </div>
        <div className="rounded-lg border border-border bg-panel p-4">
          <p className="text-xs uppercase tracking-wide text-muted">Next run</p>
          <p className="mt-2 text-sm text-white">
            {formatDateTime(status?.settings.next_run_at)}
          </p>
          <p className="mt-1 text-xs text-muted">
            last enqueue {formatDateTime(status?.settings.last_run_at)}
          </p>
        </div>
        <div className="rounded-lg border border-border bg-panel p-4">
          <p className="text-xs uppercase tracking-wide text-muted">Market</p>
          <p className="mt-2 text-lg font-semibold text-white">
            {status?.market_open ? "Open" : "Closed"}
          </p>
          <p className="mt-1 text-xs text-muted">
            {status?.settings.timezone ?? "Asia/Kolkata"} ·{" "}
            {status?.settings.market_open_time}–{status?.settings.market_close_time}
          </p>
        </div>
        <div className="rounded-lg border border-border bg-panel p-4">
          <p className="text-xs uppercase tracking-wide text-muted">
            Data freshness
          </p>
          <p className="mt-2 text-sm text-white">
            {formatDateTime(status?.data_freshness_at)}
          </p>
          <p className="mt-1 text-xs text-muted">
            server {formatDateTime(status?.server_time)}
          </p>
        </div>
      </div>

      <div className="rounded-lg border border-border bg-panel p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-white">Current job</h2>
          {active ? (
            <span
              className={`rounded px-2 py-0.5 text-xs ${statusClass(active.status)}`}
            >
              {active.status}
            </span>
          ) : (
            <span className="text-xs text-muted">Idle</span>
          )}
        </div>

        {active ? (
          <div className="mt-3 space-y-2">
            <p className="text-xs text-muted">
              #{active.id} · {active.job_type} · {active.trigger_source} ·{" "}
              {active.stage ?? "queued"}
            </p>
            <div className="h-2 w-full overflow-hidden rounded bg-white/5">
              <div
                className="h-full rounded bg-accent transition-all"
                style={{ width: `${percent}%` }}
              />
            </div>
            <p className="text-xs text-muted">
              {formatCount(active.processed_instruments)} /{" "}
              {formatCount(active.total_instruments)} instruments ·{" "}
              {formatCount(active.failed_instruments)} failed ·{" "}
              {formatCount(active.candles_inserted + active.candles_updated)}{" "}
              candles
            </p>
            {active.error_summary ? (
              <p className="text-xs text-red-300">{active.error_summary}</p>
            ) : null}
          </div>
        ) : (
          <p className="mt-2 text-xs text-muted">
            No pending or running pipeline job.
          </p>
        )}
      </div>
    </section>
  );
}
