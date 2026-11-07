export const dynamic = "force-dynamic";

import Link from "next/link";

import { CandlestickChart } from "@/components/CandlestickChart";
import { Header } from "@/components/Header";
import { ApiError } from "@/lib/api";
import { formatDateTime, formatNumber } from "@/lib/format";
import { authHeaders } from "@/lib/serverAuth";
import { getScanChart } from "@/services/marketData";
import type { ScanChartResponse } from "@/types/api";

export default async function ChartPage({
  params,
}: {
  params: Promise<{ symbol: string }>;
}) {
  const { symbol: rawSymbol } = await params;
  let symbol = rawSymbol;
  try {
    symbol = decodeURIComponent(rawSymbol);
  } catch {
    // Keep the raw segment when it is not valid percent-encoding.
  }

  let chart: ScanChartResponse | null = null;
  let error: string | null = null;

  try {
    chart = await getScanChart(symbol, 240, await authHeaders());
  } catch (caught) {
    error =
      caught instanceof ApiError
        ? `${caught.status}: ${caught.message}`
        : "The FastAPI backend is unreachable.";
  }

  return (
    <>
      <Header
        title={chart ? chart.symbol : symbol}
        subtitle={
          chart
            ? `${chart.underlying_symbol} · expiry ${chart.expiry_date} · 1-hour candles`
            : "1-hour futures chart"
        }
      />

      <main className="flex-1 space-y-6 p-6">
        <Link href="/dashboard/scanner" className="text-xs text-muted hover:text-white">
          ← Current scan
        </Link>

        {error ? (
          <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-4 text-sm text-amber-100">
            {error}
            <p className="mt-2 text-xs text-amber-100/70">
              Charts need stored candles. Refresh FYERS and run ingestion first.
            </p>
          </div>
        ) : null}

        {chart ? (
          <>
            <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-lg border border-border bg-panel p-4">
                <p className="text-xs uppercase tracking-wide text-muted">Pattern</p>
                <p className="mt-2 text-lg font-semibold text-white">
                  {chart.pattern?.classification ?? "No active match"}
                </p>
                {chart.pattern ? (
                  <p className="mt-1 text-xs text-muted">
                    {chart.pattern.candle_count} candles ·{" "}
                    {formatNumber(chart.pattern.distance_pct, 3)}% from AVWAP
                  </p>
                ) : null}
              </div>
              <div className="rounded-lg border border-border bg-panel p-4">
                <p className="text-xs uppercase tracking-wide text-muted">Scan</p>
                <p className="mt-2 text-lg font-semibold text-white">
                  {chart.scan_run_id ? `#${chart.scan_run_id}` : "—"}
                </p>
                <p className="mt-1 text-xs text-muted">
                  {formatDateTime(chart.scan_completed_at)}
                </p>
              </div>
              <div className="rounded-lg border border-border bg-panel p-4">
                <p className="text-xs uppercase tracking-wide text-muted">Pattern window</p>
                <p className="mt-2 text-sm text-white">
                  {formatDateTime(chart.pattern?.pattern_start)}
                </p>
                <p className="mt-1 text-xs text-muted">
                  to {formatDateTime(chart.pattern?.pattern_end)}
                </p>
              </div>
              <div className="rounded-lg border border-border bg-panel p-4">
                <p className="text-xs uppercase tracking-wide text-muted">Candles shown</p>
                <p className="mt-2 text-lg font-semibold text-white">
                  {chart.points.length}
                </p>
                <p className="mt-1 text-xs text-muted">
                  timeframe {chart.timeframe} min
                </p>
              </div>
            </section>

            <CandlestickChart
              points={chart.points}
              patternStart={chart.pattern?.pattern_start ?? null}
              patternEnd={chart.pattern?.pattern_end ?? null}
            />

            <p className="text-xs text-muted">
              Red: contract-start AVWAP. Blue: session VWAP. Highlighted region:
              candles detected by the latest scan for this symbol.
            </p>
          </>
        ) : null}
      </main>
    </>
  );
}
