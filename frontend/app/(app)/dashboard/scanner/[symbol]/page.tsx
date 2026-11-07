export const dynamic = "force-dynamic";

import Link from "next/link";

import { CandlestickChart } from "@/components/CandlestickChart";
import { Badge } from "@/components/ui/Badge";
import { MetricCard } from "@/components/ui/MetricCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState } from "@/components/ui/States";
import { formatDateTime, formatNumber } from "@/lib/format";
import { authHeaders } from "@/lib/serverAuth";
import { getCurrentScan, getScanChart } from "@/services/marketData";

export default async function ScannerDetailPage({
  params,
}: {
  params: Promise<{ symbol: string }>;
}) {
  const { symbol: rawSymbol } = await params;
  let symbol = rawSymbol;
  try {
    symbol = decodeURIComponent(rawSymbol);
  } catch {
    // keep raw
  }

  const headers = await authHeaders();
  let scan = null;
  let chart = null;
  try {
    scan = await getCurrentScan(headers);
  } catch {
    scan = null;
  }
  try {
    chart = await getScanChart(symbol, 240, headers);
  } catch {
    chart = null;
  }

  const result = scan?.results.find((row) => row.symbol === symbol) ?? null;

  return (
    <>
      <PageHeader
        eyebrow="Scanner match"
        title={symbol}
        description="Stored scan fields and candle context for this contract."
        breadcrumbs={[
          { href: "/dashboard", label: "Dashboard" },
          { href: "/dashboard/scanner", label: "Current Scanner" },
          { href: `/dashboard/scanner/${encodeURIComponent(symbol)}`, label: symbol },
        ]}
        actions={
          <Link
            href={`/dashboard/chart/${encodeURIComponent(symbol)}`}
            className="rounded-lg bg-mint px-3 py-1.5 text-xs font-medium text-[#04120b] hover:bg-[#3bf19c]"
          >
            Open full chart
          </Link>
        }
      />
      <main className="space-y-5 p-4 sm:p-6 lg:p-8">
        {!result ? (
          <EmptyState
            title="No active scanner match"
            description="This symbol is not present in the latest completed scan snapshot. It may have matched in an earlier scan."
            action={{ href: "/dashboard/history", label: "Browse scan history" }}
          />
        ) : (
          <>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <MetricCard label="Last price" value={formatNumber(result.last_price)} hint={result.expiry_date} />
              <MetricCard label="Contract AVWAP" value={formatNumber(result.avwap)} hint="Anchored at contract start" />
              <MetricCard label="Session VWAP" value={formatNumber(result.session_vwap)} hint="Resets each session" />
              <MetricCard
                label="Distance from AVWAP"
                value={`${formatNumber(result.distance_pct, 3)}%`}
                hint={result.classification}
              />
            </div>

            <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
              <div className="rounded-2xl border border-white/[0.06] bg-card p-5">
                <h2 className="text-sm font-semibold text-[#F5F7FA]">Why this contract matched</h2>
                <ul className="mt-3 space-y-2 text-xs text-[#DCE4EE]">
                  <li>
                    · Latest completed close was{" "}
                    <span className="font-mono">{formatNumber(result.distance_pct, 3)}%</span>{" "}
                    from contract AVWAP.
                  </li>
                  <li>
                    · The qualifying window contained{" "}
                    <span className="font-mono">{result.candle_count}</span> candle
                    {result.candle_count === 1 ? "" : "s"}.
                  </li>
                  <li>
                    · Average candle body ratio was{" "}
                    <span className="font-mono">{formatNumber(result.avg_body_ratio, 3)}</span>{" "}
                    (max {formatNumber(result.max_body_ratio, 3)}), consistent with small candles.
                  </li>
                  <li>
                    · Pattern classification:{" "}
                    <Badge tone="mint">{result.classification}</Badge>
                  </li>
                  <li>
                    · Detected at {formatDateTime(result.detected_at)}; pattern window{" "}
                    {formatDateTime(result.pattern_start)} → {formatDateTime(result.pattern_end)}.
                  </li>
                  <li>
                    · Latest ATR at detection:{" "}
                    <span className="font-mono">{formatNumber(result.latest_atr)}</span>.
                  </li>
                </ul>
                <p className="mt-4 text-[11px] leading-relaxed text-mist/70">
                  These are the stored fields from the scan snapshot. No additional
                  signals or predictions are inferred.
                </p>
              </div>

              <div className="rounded-2xl border border-white/[0.06] bg-card p-5">
                <h2 className="text-sm font-semibold text-[#F5F7FA]">Snapshot</h2>
                <dl className="mt-3 space-y-2 text-xs">
                  {[
                    ["Scan", scan ? `#${scan.id}` : "—"],
                    ["Scan completed", formatDateTime(scan?.completed_at)],
                    ["Result ID", String(result.id)],
                    ["Expiry", result.expiry_date],
                    ["Config version", scan?.config_version ?? "—"],
                  ].map(([label, value]) => (
                    <div key={label} className="flex justify-between gap-3 border-b border-white/[0.05] pb-2 last:border-0">
                      <dt className="text-mist">{label}</dt>
                      <dd className="font-mono text-[#DCE4EE]">{value}</dd>
                    </div>
                  ))}
                </dl>
                <Link
                  href={`/dashboard/history/${scan?.id}`}
                  className="mt-3 inline-block text-xs text-mint hover:underline"
                >
                  Open scan snapshot →
                </Link>
              </div>
            </div>

            {chart ? (
              <CandlestickChart
                points={chart.points}
                patternStart={chart.pattern?.pattern_start ?? null}
                patternEnd={chart.pattern?.pattern_end ?? null}
              />
            ) : (
              <EmptyState
                title="Chart data unavailable"
                description="Stored candles are not available for this symbol yet."
              />
            )}
          </>
        )}
      </main>
    </>
  );
}
