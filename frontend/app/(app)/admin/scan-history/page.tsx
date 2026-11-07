export const dynamic = "force-dynamic";

import Link from "next/link";

import { Header } from "@/components/Header";
import { RunScanButton } from "@/components/RunScanButton";
import { StatCard } from "@/components/StatCard";
import { ApiError } from "@/lib/api";
import { formatCount, formatDateTime, formatNumber } from "@/lib/format";
import { getLatestScan, getScans } from "@/services/marketData";
import type { ScanRunDetail, ScanRunPage } from "@/types/api";

export default async function AdminScansPage() {
  const adminKey = process.env.ADMIN_API_KEY;
  let runs: ScanRunPage | null = null;
  let latest: ScanRunDetail | null = null;
  let error: string | null = null;

  if (!adminKey) {
    error = "Set ADMIN_API_KEY in frontend/.env.local to run and inspect scans.";
  } else {
    try {
      runs = await getScans(adminKey, { pageSize: 20 });
    } catch (caught) {
      error =
        caught instanceof ApiError
          ? `${caught.status}: ${caught.message}`
          : "The FastAPI backend is unreachable.";
    }
    try {
      latest = await getLatestScan(adminKey);
    } catch (caught) {
      if (!(caught instanceof ApiError && caught.status === 404)) {
        error =
          error ??
          (caught instanceof ApiError
            ? `${caught.status}: ${caught.message}`
            : "Could not load the latest scan.");
      }
    }
  }

  const results = (latest?.results ?? [])
    .slice()
    .sort((a, b) => Math.abs(a.distance_pct) - Math.abs(b.distance_pct));

  return (
    <>
      <Header
        title="Admin · Scans"
        subtitle="Run the scanner on stored candles and inspect immutable snapshots"
      />

      <main className="flex-1 space-y-6 p-6">
        <div className="flex items-center justify-between">
          <Link href="/admin" className="text-xs text-muted hover:text-white">
            ← Market data diagnostics
          </Link>
          <RunScanButton />
        </div>

        {error ? (
          <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-4 text-sm text-amber-100">
            {error}
          </div>
        ) : null}

        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Latest scan"
            value={latest ? `#${latest.id}` : "None"}
            hint={latest ? `${latest.status} · ${latest.scan_type}` : "Run a scan"}
          />
          <StatCard
            label="Contracts scanned"
            value={formatCount(latest?.instruments_scanned)}
            hint={`config ${latest?.config_version ?? "—"}`}
          />
          <StatCard
            label="Matches"
            value={formatCount(latest?.matches_count)}
            hint={latest ? formatDateTime(latest.completed_at) : "—"}
          />
          <StatCard
            label="Data freshness"
            value={latest?.data_freshness_at ? "Stored" : "Unknown"}
            hint={formatDateTime(latest?.data_freshness_at)}
          />
        </section>

        <section className="space-y-3">
          <h2 className="text-sm font-semibold text-white">
            Latest scan results
          </h2>
          <div className="overflow-x-auto rounded-lg border border-border bg-panel">
            <table className="min-w-full divide-y divide-border text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-muted">
                <tr>
                  <th className="px-4 py-3">Symbol</th>
                  <th className="px-4 py-3">Expiry</th>
                  <th className="px-4 py-3">Class</th>
                  <th className="px-4 py-3">Last</th>
                  <th className="px-4 py-3">AVWAP</th>
                  <th className="px-4 py-3">VWAP</th>
                  <th className="px-4 py-3">Dist %</th>
                  <th className="px-4 py-3">Candles</th>
                  <th className="px-4 py-3">Detected</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {results.map((result) => (
                  <tr key={result.id} className="hover:bg-white/[0.02]">
                    <td className="px-4 py-3 font-mono text-xs text-white">
                      {result.symbol}
                    </td>
                    <td className="px-4 py-3 text-muted">
                      {result.expiry_date}
                    </td>
                    <td className="px-4 py-3 text-muted">
                      {result.classification}
                    </td>
                    <td className="px-4 py-3 text-muted">
                      {formatNumber(result.last_price)}
                    </td>
                    <td className="px-4 py-3 text-muted">
                      {formatNumber(result.avwap)}
                    </td>
                    <td className="px-4 py-3 text-muted">
                      {formatNumber(result.session_vwap)}
                    </td>
                    <td className="px-4 py-3 text-muted">
                      {formatNumber(result.distance_pct, 3)}
                    </td>
                    <td className="px-4 py-3 text-muted">
                      {result.candle_count}
                    </td>
                    <td className="px-4 py-3 text-muted">
                      {formatDateTime(result.detected_at)}
                    </td>
                  </tr>
                ))}
                {latest && results.length === 0 ? (
                  <tr>
                    <td className="px-4 py-6 text-muted" colSpan={9}>
                      This scan completed with no matches.
                    </td>
                  </tr>
                ) : null}
                {!latest ? (
                  <tr>
                    <td className="px-4 py-6 text-muted" colSpan={9}>
                      No completed scan yet. Click <strong>Run scan now</strong>.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>

        <section className="space-y-3">
          <h2 className="text-sm font-semibold text-white">Scan history</h2>
          <div className="overflow-x-auto rounded-lg border border-border bg-panel">
            <table className="min-w-full divide-y divide-border text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-muted">
                <tr>
                  <th className="px-4 py-3">Run</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Scanned</th>
                  <th className="px-4 py-3">Matches</th>
                  <th className="px-4 py-3">Config</th>
                  <th className="px-4 py-3">Completed</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {(runs?.items ?? []).map((run) => (
                  <tr key={run.id} className="hover:bg-white/[0.02]">
                    <td className="px-4 py-3 font-mono text-xs text-white">
                      <Link
                        href={`/admin/scan-history/${run.id}`}
                        className="hover:underline"
                      >
                        #{run.id}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-muted">{run.scan_type}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded px-2 py-0.5 text-xs ${
                          run.status === "COMPLETED"
                            ? "bg-emerald-500/10 text-emerald-300"
                            : run.status === "FAILED"
                              ? "bg-red-500/10 text-red-300"
                              : "bg-amber-500/10 text-amber-300"
                        }`}
                      >
                        {run.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-muted">
                      {formatCount(run.instruments_scanned)}
                    </td>
                    <td className="px-4 py-3 text-muted">
                      {formatCount(run.matches_count)}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-muted">
                      {run.config_version}
                    </td>
                    <td className="px-4 py-3 text-muted">
                      {formatDateTime(run.completed_at)}
                    </td>
                  </tr>
                ))}
                {runs && runs.items.length === 0 ? (
                  <tr>
                    <td className="px-4 py-6 text-muted" colSpan={7}>
                      No scan runs recorded yet.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </>
  );
}
