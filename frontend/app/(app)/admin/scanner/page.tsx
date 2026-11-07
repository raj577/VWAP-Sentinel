export const dynamic = "force-dynamic";

import Link from "next/link";

import { PageHeader } from "@/components/ui/PageHeader";
import { MetricCard } from "@/components/ui/MetricCard";
import { IntegrationPlaceholder } from "@/components/ui/States";
import { formatDateTime } from "@/lib/format";
import { getLatestScan } from "@/services/marketData";

export default async function AdminScannerConfigPage() {
  const adminKey = process.env.ADMIN_API_KEY;
  let scan = null;
  try {
    if (adminKey) scan = await getLatestScan(adminKey);
  } catch {
    scan = null;
  }

  return (
    <>
      <PageHeader
        eyebrow="Market operations"
        title="Scanner Configuration"
        description="Configuration version and publishing controls."
        breadcrumbs={[
          { href: "/admin", label: "Admin" },
          { href: "/admin/scanner", label: "Scanner Configuration" },
        ]}
        actions={
          <Link
            href="/admin/scheduler"
            className="rounded-lg border border-white/10 px-3 py-1.5 text-xs hover:bg-white/5"
          >
            Run scanner
          </Link>
        }
      />
      <main className="space-y-5 p-4 sm:p-6 lg:p-8">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Active config version"
            value={scan?.config_version ?? "—"}
            hint={scan ? `from scan #${scan.id}` : "No completed scan"}
            unavailable={!scan}
          />
          <MetricCard
            label="Scanned contracts"
            value={scan?.instruments_scanned ?? "—"}
            hint={scan ? formatDateTime(scan.completed_at) : undefined}
            unavailable={!scan}
          />
          <MetricCard
            label="Failed instruments"
            value={scan?.failed_instruments ?? "—"}
            hint="Latest scan"
            unavailable={!scan}
          />
          <MetricCard label="Draft config" value="—" hint="Publishing API not implemented" unavailable />
        </div>

        <div className="rounded-2xl border border-white/[0.06] bg-card p-5">
          <h2 className="text-sm font-semibold text-[#F5F7FA]">Current snapshot configuration</h2>
          <p className="mt-1 text-xs text-mist">
            Historical snapshots store the configuration version and their own frozen results.
            Publishing new thresholds will create new snapshots, never rewrite old ones.
          </p>
          <pre className="mt-3 overflow-auto rounded-xl bg-ink/70 p-4 font-mono text-[11px] text-mist">
{scan ? JSON.stringify(scan.config_version, null, 2) : "No scan configuration available."}
          </pre>
        </div>

        <IntegrationPlaceholder
          title="Scanner configuration API not implemented"
          description="The backend currently applies the default PatternConfig. An editable threshold editor requires a versioned configuration API and an explicit publish action."
          endpoints={[
            "GET /api/v1/admin/scanner/config",
            "POST /api/v1/admin/scanner/config",
            "POST /api/v1/admin/scanner/config/publish",
          ]}
        />
      </main>
    </>
  );
}
