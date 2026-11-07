export const dynamic = "force-dynamic";

import Link from "next/link";

import { PageHeader } from "@/components/ui/PageHeader";
import { MetricCard } from "@/components/ui/MetricCard";
import { ErrorState, IntegrationPlaceholder } from "@/components/ui/States";
import { formatDateTime } from "@/lib/format";
import { getSchedulerStatus } from "@/services/marketData";

export default async function AdminSettingsPage() {
  const adminKey = process.env.ADMIN_API_KEY;
  let scheduler = null;
  let error: string | null = null;

  if (!adminKey) {
    error = "ADMIN_API_KEY is not configured.";
  } else {
    try {
      scheduler = await getSchedulerStatus(adminKey);
    } catch {
      error = "Scheduler settings are unavailable.";
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Platform"
        title="System Settings"
        description="Only settings backed by real configuration APIs are editable. Missing categories are documented, not simulated."
        breadcrumbs={[
          { href: "/admin", label: "Admin" },
          { href: "/admin/settings", label: "Settings" },
        ]}
      />
      <main className="space-y-5 p-4 sm:p-6 lg:p-8">
        {error ? <ErrorState message={error} /> : null}

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Scheduler"
            value={scheduler?.settings.scheduler_enabled ? "Enabled" : "Paused"}
            hint={`${scheduler?.settings.scan_interval_minutes ?? "—"} minute interval`}
          />
          <MetricCard
            label="Market window"
            value={scheduler ? `${scheduler.settings.market_open_time}–${scheduler.settings.market_close_time}` : "—"}
            hint={scheduler?.settings.timezone}
          />
          <MetricCard
            label="Next run"
            value={formatDateTime(scheduler?.settings.next_run_at)}
            hint="Asia/Kolkata display"
          />
          <MetricCard label="Notifications" value="—" hint="Notification API not implemented" unavailable />
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border border-white/[0.06] bg-card p-5">
            <h2 className="text-sm font-semibold text-[#F5F7FA]">Implemented settings</h2>
            <ul className="mt-3 space-y-2 text-xs text-mist">
              <li>
                · Market data and scheduler:{" "}
                <Link href="/admin/scheduler" className="text-mint hover:underline">
                  Scheduler controls
                </Link>
              </li>
              <li>
                · FYERS connection and instruments:{" "}
                <Link href="/admin/market-data" className="text-mint hover:underline">
                  Market data
                </Link>
              </li>
              <li>· Authentication secrets and email provider are environment-managed and not editable from the UI.</li>
            </ul>
          </div>

          <IntegrationPlaceholder
            title="General, subscription and notification settings pending"
            description="These categories require dedicated backend settings APIs with audit logging. They are intentionally absent to avoid fake controls."
            endpoints={[
              "GET/PATCH /api/v1/admin/settings/general",
              "GET/PATCH /api/v1/admin/settings/subscription",
              "GET/PATCH /api/v1/admin/settings/notifications",
            ]}
          />
        </div>
      </main>
    </>
  );
}
