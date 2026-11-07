export const dynamic = "force-dynamic";

import Link from "next/link";

import { ScanResultsTable } from "@/components/ScanResultsTable";
import { MetricCard } from "@/components/ui/MetricCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/States";
import { formatDateTime } from "@/lib/format";
import { authHeaders, requireUser } from "@/lib/serverAuth";
import { getCurrentScan, getMarketDataStatus, getScanHistory } from "@/services/marketData";
import type { MarketDataStatus, ScanRunDetail, ScanRunPage } from "@/types/api";

export default async function CustomerDashboardPage() {
  const user = await requireUser();
  const headers = await authHeaders();

  let scan: ScanRunDetail | null = null;
  let market: MarketDataStatus | null = null;
  let history: ScanRunPage | null = null;

  try {
    scan = await getCurrentScan(headers);
  } catch {
    scan = null;
  }
  try {
    market = await getMarketDataStatus();
  } catch {
    market = null;
  }
  try {
    history = await getScanHistory({ pageSize: 5 }, headers);
  } catch {
    history = null;
  }

  const results = scan?.results ?? [];
  const patterns = {
    touch: results.filter((row) => row.classification === "AVWAP TOUCH").length,
    hugging: results.filter((row) => row.classification === "AVWAP HUGGING").length,
    consolidation: results.filter((row) => row.classification === "AVWAP CONSOLIDATION").length,
  };

  return (
    <>
      <PageHeader
        eyebrow="Research workspace"
        title={`Welcome, ${user.full_name.split(" ")[0]}`}
        description="Latest scanner snapshot, market-data freshness and subscription status."
        breadcrumbs={[{ href: "/dashboard", label: "Dashboard" }]}
        actions={
          <Link
            href="/dashboard/scanner"
            className="rounded-lg bg-mint px-3 py-1.5 text-xs font-medium text-[#04120b] hover:bg-[#3bf19c]"
          >
            Open scanner
          </Link>
        }
      />

      <main className="space-y-5 p-4 sm:p-6 lg:p-8">
        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Matching futures"
            value={results.length}
            hint={scan ? `Scan #${scan.id}` : "No completed scan"}
          />
          <MetricCard
            label="AVWAP Touch"
            value={patterns.touch}
            hint={`${patterns.hugging} hugging · ${patterns.consolidation} consolidation`}
          />
          <MetricCard
            label="Latest scan"
            value={scan ? `#${scan.id}` : "—"}
            hint={formatDateTime(scan?.completed_at)}
            unavailable={!scan}
          />
          <MetricCard
            label="Data freshness"
            value={formatDateTime(market?.latest_candle_at)}
            hint={
              market
                ? `${market.instruments_active} active contracts`
                : "Market data unavailable"
            }
            unavailable={!market}
          />
        </section>

        <section className="grid gap-4 lg:grid-cols-[1.4fr_0.6fr]">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-[#F5F7FA]">Latest scanner results</h2>
                <p className="text-xs text-mist">
                  {scan
                    ? `${scan.matches_count} matches · snapshot ${formatDateTime(scan.completed_at)}`
                    : "Run market data and a scan to populate this view."}
                </p>
              </div>
              <Link href="/dashboard/scanner" className="text-xs text-mint hover:underline">
                Full scanner →
              </Link>
            </div>
            {scan ? (
              <ScanResultsTable results={results.slice(0, 8)} />
            ) : (
              <EmptyState
                title="No scan snapshot yet"
                description="Once the platform completes a scan, matching contracts appear here with immutable timestamps."
              />
            )}
          </div>

          <aside className="space-y-4">
            <div className="rounded-2xl border border-white/[0.06] bg-card p-4">
              <h2 className="text-sm font-semibold text-[#F5F7FA]">Subscription</h2>
              <p className="mt-2 text-xs text-mist">
                Plan and entitlement APIs are not implemented yet, so no plan or
                trial state is shown.
              </p>
              <Link href="/dashboard/subscription" className="mt-3 inline-block text-xs text-mint hover:underline">
                Subscription details →
              </Link>
            </div>

            <div className="rounded-2xl border border-white/[0.06] bg-card p-4">
              <h2 className="text-sm font-semibold text-[#F5F7FA]">Watchlist</h2>
              <p className="mt-2 text-xs text-mist">
                Watchlists require a backend API that is not implemented yet.
              </p>
              <Link href="/dashboard/watchlist" className="mt-3 inline-block text-xs text-sky hover:underline">
                Watchlist status →
              </Link>
            </div>

            <div className="rounded-2xl border border-white/[0.06] bg-card p-4">
              <h2 className="text-sm font-semibold text-[#F5F7FA]">Market connection</h2>
              <div className="mt-2 flex items-center gap-2 text-xs text-mist">
                <StatusBadge status={market?.fyers.status ?? "NOT_CONFIGURED"} />
              </div>
              <p className="mt-2 text-[11px] text-mist/70">
                {market?.fyers.message ?? "Status unavailable."}
              </p>
            </div>
          </aside>
        </section>

        <section className="rounded-2xl border border-white/[0.06] bg-card p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-[#F5F7FA]">Recent scan history</h2>
            <Link href="/dashboard/history" className="text-xs text-mint hover:underline">
              All scans →
            </Link>
          </div>
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-[640px] w-full text-left text-xs">
              <thead className="text-[10px] uppercase tracking-wider text-mist">
                <tr>
                  <th className="py-2 pr-4 font-medium">Scan</th>
                  <th className="py-2 pr-4 font-medium">Completed</th>
                  <th className="py-2 pr-4 font-medium">Contracts</th>
                  <th className="py-2 pr-4 font-medium">Matches</th>
                  <th className="py-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.05]">
                {(history?.items ?? []).map((run) => (
                  <tr key={run.id}>
                    <td className="py-2 pr-4 font-mono text-[#F5F7FA]">
                      <Link href={`/dashboard/history/${run.id}`} className="hover:underline">
                        #{run.id}
                      </Link>
                    </td>
                    <td className="py-2 pr-4 text-mist">{formatDateTime(run.completed_at)}</td>
                    <td className="py-2 pr-4 text-mist">{run.instruments_scanned}</td>
                    <td className="py-2 pr-4 text-mist">{run.matches_count}</td>
                    <td className="py-2"><StatusBadge status={run.status} /></td>
                  </tr>
                ))}
                {history && history.items.length === 0 ? (
                  <tr><td colSpan={5} className="py-4 text-mist">No scan history yet.</td></tr>
                ) : null}
                {!history ? (
                  <tr><td colSpan={5} className="py-4 text-mist">Scan history unavailable.</td></tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </>
  );
}
