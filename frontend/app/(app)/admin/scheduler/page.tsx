export const dynamic = "force-dynamic";

import { Header } from "@/components/Header";
import { PipelineJobsPanel } from "@/components/PipelineJobsPanel";
import { SchedulerControls } from "@/components/SchedulerControls";
import { SchedulerLivePanel } from "@/components/SchedulerLivePanel";
import { StatCard } from "@/components/StatCard";
import { ApiError } from "@/lib/api";
import { formatCount } from "@/lib/format";
import {
  getPipelineJobs,
  getPipelineSummary,
  getSchedulerStatus,
} from "@/services/marketData";
import type {
  PipelineJobPage,
  PipelineSummary,
  SchedulerStatus,
} from "@/types/api";

export default async function AdminPipelinePage() {
  const adminKey = process.env.ADMIN_API_KEY;
  let status: SchedulerStatus | null = null;
  let jobs: PipelineJobPage | null = null;
  let summary: PipelineSummary | null = null;
  let error: string | null = null;

  if (!adminKey) {
    error = "Set ADMIN_API_KEY in frontend/.env.local to manage the scheduler.";
  } else {
    try {
      [status, jobs, summary] = await Promise.all([
        getSchedulerStatus(adminKey),
        getPipelineJobs(adminKey, { pageSize: 20 }),
        getPipelineSummary(adminKey),
      ]);
    } catch (caught) {
      error =
        caught instanceof ApiError
          ? `${caught.status}: ${caught.message}`
          : "The FastAPI backend is unreachable.";
    }
  }

  return (
    <>
      <Header
        title="Admin · Market Data & Scheduler"
        subtitle="Automated 56-minute pipeline, manual controls and job monitoring"
      />

      <main className="flex-1 space-y-6 p-6">
        {error ? (
          <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-4 text-sm text-amber-100">
            {error}
          </div>
        ) : null}

        {summary ? (
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Total jobs"
              value={formatCount(summary.total_jobs)}
              hint={`${formatCount(summary.counts.COMPLETED ?? 0)} completed`}
            />
            <StatCard
              label="Failed jobs"
              value={formatCount(summary.counts.FAILED ?? 0)}
              hint={`last ${summary.last_failed_at ?? "never"}`}
            />
            <StatCard
              label="Running"
              value={formatCount(summary.counts.RUNNING ?? 0)}
              hint={`${formatCount(summary.counts.PENDING ?? 0)} pending`}
            />
            <StatCard
              label="Last scan run"
              value={
                summary.last_scan_run_id ? `#${summary.last_scan_run_id}` : "—"
              }
              hint="latest immutable snapshot"
            />
          </section>
        ) : null}

        <SchedulerLivePanel initial={status} />

        {status ? <SchedulerControls settings={status.settings} /> : null}

        <PipelineJobsPanel initial={jobs} />
      </main>
    </>
  );
}
