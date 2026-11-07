export const dynamic = "force-dynamic";

import Link from "next/link";

import { PageHeader } from "@/components/ui/PageHeader";
import { PipelineJobsPanel } from "@/components/PipelineJobsPanel";
import { ErrorState } from "@/components/ui/States";
import { ApiError } from "@/lib/api";
import { getPipelineJobs } from "@/services/marketData";
import type { PipelineJobPage } from "@/types/api";

export default async function AdminJobsPage() {
  const adminKey = process.env.ADMIN_API_KEY;
  let jobs: PipelineJobPage | null = null;
  let error: string | null = null;

  if (!adminKey) {
    error = "ADMIN_API_KEY is not configured.";
  } else {
    try {
      jobs = await getPipelineJobs(adminKey, { pageSize: 20 });
    } catch (caught) {
      error =
        caught instanceof ApiError
          ? `${caught.status}: ${caught.message}`
          : "The FastAPI backend is unreachable.";
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Market operations"
        title="Pipeline Jobs"
        description="Ingestion and scanner executions with per-instrument logs and cooperative cancellation."
        breadcrumbs={[
          { href: "/admin", label: "Admin" },
          { href: "/admin/jobs", label: "Pipeline Jobs" },
        ]}
        actions={
          <Link
            href="/admin/scheduler"
            className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-[#F5F7FA] hover:bg-white/5"
          >
            Scheduler controls
          </Link>
        }
      />
      <main className="space-y-5 p-4 sm:p-6 lg:p-8">
        {error ? <ErrorState message={error} /> : null}
        <PipelineJobsPanel initial={jobs} />
      </main>
    </>
  );
}
