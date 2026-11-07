"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { formatCount, formatDateTime } from "@/lib/format";
import type { PipelineJobPage } from "@/types/api";

const STATUS_OPTIONS = [
  "",
  "PENDING",
  "RUNNING",
  "COMPLETED",
  "PARTIALLY_COMPLETED",
  "FAILED",
  "CANCELLED",
];

function statusClass(status: string): string {
  if (status === "COMPLETED") return "bg-emerald-500/10 text-emerald-300";
  if (status === "FAILED") return "bg-red-500/10 text-red-300";
  if (status === "CANCELLED") return "bg-white/5 text-muted";
  if (status === "PARTIALLY_COMPLETED" || status === "RUNNING")
    return "bg-amber-500/10 text-amber-300";
  return "bg-sky-500/10 text-sky-300";
}

export function PipelineJobsPanel({
  initial,
}: {
  initial: PipelineJobPage | null;
}) {
  const router = useRouter();
  const [data, setData] = useState<PipelineJobPage | null>(initial);
  const [page, setPage] = useState(initial?.page ?? 1);
  const [statusFilter, setStatusFilter] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const query = new URLSearchParams({
      page: String(page),
      page_size: "20",
    });
    if (statusFilter) query.set("status", statusFilter);
    try {
      const response = await fetch(`/api/admin/pipeline/jobs?${query}`, {
        cache: "no-store",
      });
      if (!response.ok) return;
      setData((await response.json()) as PipelineJobPage);
    } catch {
      // keep previous data
    }
  }, [page, statusFilter]);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 5000);
    return () => window.clearInterval(timer);
  }, [load]);

  async function cancel(jobId: number) {
    if (!window.confirm(`Request cancellation for job #${jobId}?`)) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`/api/admin/pipeline/jobs/${jobId}/cancel`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason: "Cancelled from admin dashboard" }),
        cache: "no-store",
      });
      if (!response.ok) {
        const body = (await response.json()) as { detail?: string };
        setError(body.detail ?? "Cancellation failed.");
        return;
      }
      await load();
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total / 20)) : 1;

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-white">Pipeline jobs</h2>
        <div className="flex items-center gap-2 text-xs text-muted">
          <select
            value={statusFilter}
            onChange={(event) => {
              setStatusFilter(event.target.value);
              setPage(1);
            }}
            className="rounded-md border border-border bg-base px-2 py-1.5 text-xs text-white"
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option || "all"} value={option}>
                {option || "All statuses"}
              </option>
            ))}
          </select>
          <span>
            Page {page} / {totalPages}
          </span>
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => setPage((value) => Math.max(1, value - 1))}
            className="rounded border border-border px-2 py-1 disabled:opacity-40"
          >
            Prev
          </button>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
            className="rounded border border-border px-2 py-1 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      </div>

      {error ? <p className="text-xs text-red-300">{error}</p> : null}

      <div className="overflow-x-auto rounded-lg border border-border bg-panel">
        <table className="min-w-full divide-y divide-border text-sm">
          <thead className="text-left text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="px-4 py-3">Job</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Trigger</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Started</th>
              <th className="px-4 py-3">Duration</th>
              <th className="px-4 py-3">Processed</th>
              <th className="px-4 py-3">Failed</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {(data?.items ?? []).map((job) => (
              <tr key={job.id} className="hover:bg-white/[0.02]">
                <td className="px-4 py-3 font-mono text-xs text-white">
                  <Link
                    href={`/admin/pipeline/${job.id}`}
                    className="hover:underline"
                  >
                    #{job.id}
                  </Link>
                </td>
                <td className="px-4 py-3 text-muted">{job.job_type}</td>
                <td className="px-4 py-3 text-muted">{job.trigger_source}</td>
                <td className="px-4 py-3">
                  <span className={`rounded px-2 py-0.5 text-xs ${statusClass(job.status)}`}>
                    {job.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-muted">
                  {formatDateTime(job.started_at)}
                </td>
                <td className="px-4 py-3 text-muted">
                  {job.duration_seconds != null
                    ? `${Number(job.duration_seconds).toFixed(1)}s`
                    : "—"}
                </td>
                <td className="px-4 py-3 text-muted">
                  {formatCount(job.processed_instruments)}
                </td>
                <td className="px-4 py-3 text-muted">
                  {formatCount(job.failed_instruments)}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <Link
                      href={`/admin/pipeline/${job.id}`}
                      className="text-xs text-accent hover:underline"
                    >
                      Details
                    </Link>
                    {(job.status === "PENDING" || job.status === "RUNNING") && (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => void cancel(job.id)}
                        className="text-xs text-red-300 hover:underline disabled:opacity-50"
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {data && data.items.length === 0 ? (
              <tr>
                <td className="px-4 py-6 text-muted" colSpan={9}>
                  No pipeline jobs match this filter.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
