export const dynamic = "force-dynamic";

import Link from "next/link";

import { AutoRefresh } from "@/components/AutoRefresh";
import { Header } from "@/components/Header";
import { ApiError } from "@/lib/api";
import { formatCount, formatDateTime } from "@/lib/format";
import { getPipelineJob, getPipelineJobLogs } from "@/services/marketData";
import type { PipelineJob, PipelineLogPage } from "@/types/api";

function statusClass(status: string): string {
  if (status === "COMPLETED") return "bg-emerald-500/10 text-emerald-300";
  if (status === "FAILED") return "bg-red-500/10 text-red-300";
  if (status === "CANCELLED") return "bg-white/5 text-muted";
  if (status === "PARTIALLY_COMPLETED" || status === "RUNNING")
    return "bg-amber-500/10 text-amber-300";
  return "bg-sky-500/10 text-sky-300";
}

export default async function PipelineJobPage({
  params,
}: {
  params: Promise<{ jobId: string }>;
}) {
  const { jobId } = await params;
  const numericId = Number(jobId);
  const adminKey = process.env.ADMIN_API_KEY;

  let job: PipelineJob | null = null;
  let logs: PipelineLogPage | null = null;
  let error: string | null = null;

  if (!adminKey) {
    error = "Set ADMIN_API_KEY in frontend/.env.local.";
  } else if (!Number.isInteger(numericId) || numericId < 1) {
    error = "Invalid pipeline job id.";
  } else {
    try {
      [job, logs] = await Promise.all([
        getPipelineJob(adminKey, numericId),
        getPipelineJobLogs(adminKey, numericId, { pageSize: 500 }),
      ]);
    } catch (caught) {
      error =
        caught instanceof ApiError
          ? `${caught.status}: ${caught.message}`
          : "The FastAPI backend is unreachable.";
    }
  }

  const percent =
    job && job.total_instruments > 0
      ? Math.min(
          100,
          Math.round((job.processed_instruments / job.total_instruments) * 100),
        )
      : 0;

  return (
    <>
      <AutoRefresh />
      <Header
        title={job ? `Pipeline job #${job.id}` : "Pipeline job"}
        subtitle="Near-real-time stage, counters and per-instrument logs"
      />

      <main className="flex-1 space-y-6 p-6">
        <Link
          href="/admin/pipeline"
          className="text-xs text-muted hover:text-white"
        >
          ← Scheduler & market data
        </Link>

        {error ? (
          <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-4 text-sm text-amber-100">
            {error}
          </div>
        ) : null}

        {job ? (
          <>
            <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-lg border border-border bg-panel p-4">
                <p className="text-xs uppercase tracking-wide text-muted">Status</p>
                <p className="mt-2">
                  <span
                    className={`rounded px-2 py-0.5 text-xs ${statusClass(job.status)}`}
                  >
                    {job.status}
                  </span>
                </p>
                <p className="mt-2 text-xs text-muted">
                  {job.job_type} · {job.trigger_source} ·{" "}
                  {job.stage ?? "queued"}
                </p>
              </div>
              <div className="rounded-lg border border-border bg-panel p-4">
                <p className="text-xs uppercase tracking-wide text-muted">
                  Instruments
                </p>
                <p className="mt-2 text-lg font-semibold text-white">
                  {formatCount(job.processed_instruments)} /{" "}
                  {formatCount(job.total_instruments)}
                </p>
                <p className="mt-1 text-xs text-muted">
                  {formatCount(job.failed_instruments)} failed
                </p>
              </div>
              <div className="rounded-lg border border-border bg-panel p-4">
                <p className="text-xs uppercase tracking-wide text-muted">
                  Candles
                </p>
                <p className="mt-2 text-lg font-semibold text-white">
                  {formatCount(job.candles_inserted + job.candles_updated)}
                </p>
                <p className="mt-1 text-xs text-muted">
                  {formatCount(job.candles_inserted)} inserted ·{" "}
                  {formatCount(job.candles_updated)} updated
                </p>
              </div>
              <div className="rounded-lg border border-border bg-panel p-4">
                <p className="text-xs uppercase tracking-wide text-muted">
                  Timing
                </p>
                <p className="mt-2 text-sm text-white">
                  {job.duration_seconds != null
                    ? `${Number(job.duration_seconds).toFixed(1)}s`
                    : "running"}
                </p>
                <p className="mt-1 text-xs text-muted">
                  {formatDateTime(job.started_at)} →{" "}
                  {formatDateTime(job.completed_at)}
                </p>
              </div>
            </section>

            <section className="rounded-lg border border-border bg-panel p-4">
              <div className="h-2 w-full overflow-hidden rounded bg-white/5">
                <div
                  className="h-full rounded bg-accent transition-all"
                  style={{ width: `${percent}%` }}
                />
              </div>
              <p className="mt-2 text-xs text-muted">
                {percent}% · {" "}
                {job.ingestion_job_id
                  ? `ingestion job #${job.ingestion_job_id}`
                  : "no ingestion"}{" "}
                ·{" "}
                {job.scan_run_id ? (
                  <Link
                    href={`/scans/${job.scan_run_id}`}
                    className="text-accent hover:underline"
                  >
                    scan run #{job.scan_run_id}
                  </Link>
                ) : (
                  "no scan yet"
                )}
              </p>
              {job.cancellation_requested_at ? (
                <p className="mt-2 text-xs text-amber-300">
                  Cancellation requested {formatDateTime(job.cancellation_requested_at)}
                </p>
              ) : null}
              {job.error_summary ? (
                <pre className="mt-3 max-h-40 overflow-auto whitespace-pre-wrap rounded bg-black/30 p-3 text-xs text-red-200">
                  {job.error_summary}
                </pre>
              ) : null}
            </section>

            <section className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-white">
                  Per-instrument logs
                </h2>
                <p className="text-xs text-muted">
                  {formatCount(logs?.total)} rows
                </p>
              </div>
              <div className="max-h-[520px] overflow-auto rounded-lg border border-border bg-panel">
                <table className="min-w-full divide-y divide-border text-sm">
                  <thead className="sticky top-0 bg-panel text-left text-xs uppercase tracking-wide text-muted">
                    <tr>
                      <th className="px-4 py-3">Symbol</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3">Candles</th>
                      <th className="px-4 py-3">Error</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {(logs?.items ?? []).map((log) => (
                      <tr key={log.id}>
                        <td className="px-4 py-2 font-mono text-xs text-white">
                          {log.symbol}
                        </td>
                        <td className="px-4 py-2 text-xs text-muted">
                          {log.status}
                        </td>
                        <td className="px-4 py-2 text-xs text-muted">
                          {formatCount(log.candles_processed)}
                        </td>
                        <td className="px-4 py-2 text-xs text-red-300">
                          {log.error_message ?? ""}
                        </td>
                      </tr>
                    ))}
                    {logs && logs.items.length === 0 ? (
                      <tr>
                        <td className="px-4 py-6 text-muted" colSpan={4}>
                          No per-instrument logs for this job yet.
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        ) : null}
      </main>
    </>
  );
}
