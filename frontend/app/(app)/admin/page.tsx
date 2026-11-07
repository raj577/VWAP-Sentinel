export const dynamic = "force-dynamic";

import Link from "next/link";

import { PageHeader } from "@/components/ui/PageHeader";
import { MetricCard } from "@/components/ui/MetricCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ErrorState, IntegrationPlaceholder } from "@/components/ui/States";
import { ApiError } from "@/lib/api";
import { formatCount, formatDateTime } from "@/lib/format";
import { fetchCurrentUser } from "@/lib/serverAuth";
import {
  getAdminUsers,
  getAuditLogs,
  getLatestScan,
  getMarketDataStatus,
  getPipelineJobs,
  getPipelineSummary,
  getSchedulerStatus,
} from "@/services/marketData";
import type {
  AdminUserPage,
  MarketDataStatus,
  PipelineJobPage,
  PipelineSummary,
  ScanRunDetail,
  SchedulerStatus,
  AuditLogRow,
} from "@/types/api";

export default async function AdminOverviewPage() {
  const adminKey = process.env.ADMIN_API_KEY;
  const user = await fetchCurrentUser();
  let errors: string[] = [];

  let users: AdminUserPage | null = null;
  let market: MarketDataStatus | null = null;
  let scheduler: SchedulerStatus | null = null;
  let pipeline: PipelineSummary | null = null;
  let jobs: PipelineJobPage | null = null;
  let latestScan: ScanRunDetail | null = null;
  let audit: AuditLogRow[] = [];

  if (!adminKey) {
    return (
      <div className="p-6">
        <ErrorState message="ADMIN_API_KEY is not configured for the web app." />
      </div>
    );
  }

  const results = await Promise.allSettled([
    getAdminUsers(adminKey, { pageSize: 5 }),
    getMarketDataStatus(),
    getSchedulerStatus(adminKey),
    getPipelineSummary(adminKey),
    getPipelineJobs(adminKey, { pageSize: 5 }),
    getLatestScan(adminKey),
    getAuditLogs(adminKey, 6),
  ]);

  const [
    usersResult,
    marketResult,
    schedulerResult,
    pipelineResult,
    jobsResult,
    scanResult,
    auditResult,
  ] = results;

  if (usersResult.status === "fulfilled") users = usersResult.value;
  else errors.push("users: unavailable");
  if (marketResult.status === "fulfilled") market = marketResult.value;
  else errors.push("market data: unavailable");
  if (schedulerResult.status === "fulfilled") scheduler = schedulerResult.value;
  else errors.push("scheduler: unavailable");
  if (pipelineResult.status === "fulfilled") pipeline = pipelineResult.value;
  else errors.push("pipeline summary: unavailable");
  if (jobsResult.status === "fulfilled") jobs = jobsResult.value;
  else errors.push("pipeline jobs: unavailable");
  if (scanResult.status === "fulfilled") latestScan = scanResult.value;
  if (auditResult.status === "fulfilled") audit = auditResult.value;
  else if (user?.roles.includes("SUPER_ADMIN")) errors.push("audit logs: unavailable");

  const failedJobs = pipeline?.counts.FAILED ?? 0;
  const runningJobs = pipeline?.counts.RUNNING ?? 0;

  return (
    <>
      <PageHeader
        eyebrow="Operations"
        title="Admin Dashboard"
        description="Platform health, market data, scheduler and customer activity from live APIs."
        breadcrumbs={[{ href: "/admin", label: "Admin" }]}
        actions={
          <>
            <Link
              href="/admin/scheduler"
              className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-[#F5F7FA] hover:bg-white/5"
            >
              Scheduler
            </Link>
            <Link
              href="/admin/users"
              className="rounded-lg bg-mint px-3 py-1.5 text-xs font-medium text-[#04120b] hover:bg-[#3bf19c]"
            >
              Users
            </Link>
          </>
        }
      />

      <main className="space-y-6 p-4 sm:p-6 lg:p-8">
        {errors.length ? (
          <p className="rounded-xl border border-amber-400/20 bg-amber-400/[0.05] px-3 py-2 text-xs text-amber-200">
            Some sections are unavailable: {errors.join(", ")}.
          </p>
        ) : null}

        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Registered users"
            value={formatCount(users?.total)}
            hint={`${users?.items.length ?? 0} most recent loaded`}
          />
          <MetricCard
            label="Active contracts"
            value={formatCount(market?.instruments_active)}
            hint={`${formatCount(market?.instruments_total)} stored`}
          />
          <MetricCard
            label="Latest scan matches"
            value={formatCount(latestScan?.matches_count)}
            hint={formatDateTime(latestScan?.completed_at)}
          />
          <MetricCard
            label="Failed pipeline jobs"
            value={pipeline ? formatCount(failedJobs) : "—"}
            hint={
              pipeline
                ? `${formatCount(runningJobs)} running · ${formatCount(pipeline.total_jobs)} total`
                : "Pipeline summary unavailable"
            }
            unavailable={!pipeline}
          />
          <MetricCard label="Active subscriptions" value="—" hint="Subscription API not implemented" unavailable />
          <MetricCard label="Active trials" value="—" hint="Trial API not implemented" unavailable />
          <MetricCard label="Monthly revenue" value="—" hint="No payment data source yet" unavailable />
          <MetricCard
            label="FYERS connection"
            value={market?.fyers.status?.replaceAll("_", " ") ?? "Unknown"}
            hint={formatDateTime(market?.latest_candle_at)}
            unavailable={market?.fyers.status !== "CONNECTED"}
          />
        </section>

        <section className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border border-white/[0.06] bg-card p-5">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-[#F5F7FA]">Platform health</h2>
              <StatusBadge
                status={
                  scheduler?.settings.scheduler_enabled ? "RUNNING" : "PENDING"
                }
              />
            </div>
            <dl className="mt-4 space-y-2.5 text-xs">
              {[
                ["Market session", scheduler?.market_open ? "Open" : "Closed"],
                ["Scheduler interval", `${scheduler?.settings.scan_interval_minutes ?? "—"} min`],
                ["Next scheduled run", formatDateTime(scheduler?.settings.next_run_at)],
                ["Data freshness", formatDateTime(market?.latest_candle_at)],
                ["Stored candles", formatCount(market?.candles_total)],
                ["Active pipeline job", scheduler?.active_job ? `#${scheduler.active_job.id} · ${scheduler.active_job.status}` : "Idle"],
              ].map(([label, value]) => (
                <div key={label} className="flex items-center justify-between gap-4 border-b border-white/[0.05] pb-2 last:border-0">
                  <dt className="text-mist">{label}</dt>
                  <dd className="font-mono text-[#DCE4EE]">{value}</dd>
                </div>
              ))}
            </dl>
            <Link href="/admin/scheduler" className="mt-3 inline-block text-xs text-mint hover:underline">
              Open scheduler controls →
            </Link>
          </div>

          <div className="rounded-2xl border border-white/[0.06] bg-card p-5">
            <h2 className="text-sm font-semibold text-[#F5F7FA]">Recent pipeline jobs</h2>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-left text-xs">
                <thead className="text-[10px] uppercase tracking-wider text-mist">
                  <tr>
                    <th className="py-2 pr-3 font-medium">Job</th>
                    <th className="py-2 pr-3 font-medium">Type</th>
                    <th className="py-2 pr-3 font-medium">Status</th>
                    <th className="py-2 font-medium">Started</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.05]">
                  {(jobs?.items ?? []).map((job) => (
                    <tr key={job.id}>
                      <td className="py-2 pr-3 font-mono text-[#F5F7FA]">
                        <Link href={`/admin/jobs/${job.id}`} className="hover:underline">
                          #{job.id}
                        </Link>
                      </td>
                      <td className="py-2 pr-3 text-mist">{job.job_type}</td>
                      <td className="py-2 pr-3"><StatusBadge status={job.status} /></td>
                      <td className="py-2 text-mist">{formatDateTime(job.started_at)}</td>
                    </tr>
                  ))}
                  {jobs && jobs.items.length === 0 ? (
                    <tr><td className="py-4 text-mist" colSpan={4}>No jobs recorded.</td></tr>
                  ) : null}
                </tbody>
              </table>
            </div>
            <Link href="/admin/jobs" className="mt-3 inline-block text-xs text-mint hover:underline">
              View all jobs →
            </Link>
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border border-white/[0.06] bg-card p-5">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-[#F5F7FA]">Latest scanner matches</h2>
              {latestScan ? (
                <Link href={`/admin/scan-history/${latestScan.id}`} className="text-xs text-mint hover:underline">
                  Scan #{latestScan.id}
                </Link>
              ) : null}
            </div>
            {latestScan ? (
              <ul className="mt-3 divide-y divide-white/[0.05] text-xs">
                {latestScan.results.slice(0, 6).map((result) => (
                  <li key={result.id} className="flex items-center justify-between gap-2 py-2">
                    <span className="font-mono text-[#DCE4EE]">{result.symbol}</span>
                    <span className="text-mist">{result.classification}</span>
                    <span className="font-mono text-mist">
                      {Number(result.distance_pct).toFixed(2)}%
                    </span>
                  </li>
                ))}
                {latestScan.results.length === 0 ? (
                  <li className="py-4 text-mist">This scan completed with no matches.</li>
                ) : null}
              </ul>
            ) : (
              <p className="mt-3 text-xs text-mist">No completed scan available.</p>
            )}
          </div>

          <div className="rounded-2xl border border-white/[0.06] bg-card p-5">
            <h2 className="text-sm font-semibold text-[#F5F7FA]">Recent registrations</h2>
            <ul className="mt-3 divide-y divide-white/[0.05] text-xs">
              {(users?.items ?? []).map((account) => (
                <li key={account.id} className="flex items-center justify-between gap-2 py-2">
                  <div className="min-w-0">
                    <p className="truncate text-[#DCE4EE]">{account.full_name}</p>
                    <p className="truncate text-mist">{account.email}</p>
                  </div>
                  <StatusBadge status={account.account_status} />
                </li>
              ))}
              {users && users.items.length === 0 ? (
                <li className="py-4 text-mist">No users yet.</li>
              ) : null}
            </ul>
            <Link href="/admin/users" className="mt-3 inline-block text-xs text-mint hover:underline">
              Manage users →
            </Link>
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-2">
          <IntegrationPlaceholder
            title="Subscription and revenue metrics unavailable"
            description="Subscription plans, trials, entitlements and payments are not implemented in the backend yet. This dashboard does not display invented numbers."
            endpoints={[
              "GET /api/v1/admin/subscriptions/summary",
              "GET /api/v1/admin/trials/summary",
              "GET /api/v1/admin/payments/summary",
            ]}
          />

          <div className="rounded-2xl border border-white/[0.06] bg-card p-5">
            <h2 className="text-sm font-semibold text-[#F5F7FA]">Recent administrative activity</h2>
            {audit.length ? (
              <ul className="mt-3 divide-y divide-white/[0.05] text-xs">
                {audit.map((row) => (
                  <li key={row.id} className="py-2">
                    <p className="font-mono text-[#DCE4EE]">{row.action}</p>
                    <p className="text-mist">
                      {formatDateTime(row.created_at)} · {row.ip_address ?? "unknown IP"}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 text-xs text-mist">
                {user?.roles.includes("SUPER_ADMIN")
                  ? "No audit events recorded."
                  : "Audit logs are visible to SUPER_ADMIN only."}
              </p>
            )}
          </div>
        </section>
      </main>
    </>
  );
}
