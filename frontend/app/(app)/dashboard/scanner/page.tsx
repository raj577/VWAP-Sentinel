export const dynamic = "force-dynamic";

import Link from "next/link";

import { ScannerWorkspace } from "@/components/customer/ScannerWorkspace";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState } from "@/components/ui/States";
import { authHeaders } from "@/lib/serverAuth";
import { getCurrentScan } from "@/services/marketData";
import type { ScanRunDetail } from "@/types/api";

export default async function CustomerScannerPage() {
  let scan: ScanRunDetail | null = null;

  try {
    scan = await getCurrentScan(await authHeaders());
  } catch {
    scan = null;
  }

  return (
    <>
      <PageHeader
        eyebrow="Scanner"
        title="Current Scanner"
        description="Contracts matching the latest completed AVWAP scan over stored 1-hour candles."
        breadcrumbs={[
          { href: "/dashboard", label: "Dashboard" },
          { href: "/dashboard/scanner", label: "Current Scanner" },
        ]}
        actions={
          <Link
            href="/dashboard/history"
            className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-[#F5F7FA] hover:bg-white/5"
          >
            Scan history
          </Link>
        }
      />
      <main className="space-y-5 p-4 sm:p-6 lg:p-8">
        {scan ? (
          <ScannerWorkspace scan={scan} />
        ) : (
          <EmptyState
            title="No completed scan available"
            description="The scanner has not produced a completed snapshot yet. Market data must be ingested and a scan executed by the platform."
            action={{ href: "/dashboard", label: "Back to dashboard" }}
          />
        )}
      </main>
    </>
  );
}
