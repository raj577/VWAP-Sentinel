import Link from "next/link";

import { formatDateTime, formatNumber } from "@/lib/format";
import type { ScanResultRow } from "@/types/api";

export function ScanResultsTable({ results }: { results: ScanResultRow[] }) {
  if (results.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-panel p-6 text-sm text-muted">
        This scan completed with no matches.
      </div>
    );
  }

  const sorted = results
    .slice()
    .sort((a, b) => Math.abs(a.distance_pct) - Math.abs(b.distance_pct));

  return (
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
            <th className="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {sorted.map((result) => (
            <tr key={result.id} className="hover:bg-white/[0.02]">
              <td className="px-4 py-3 font-mono text-xs text-white">
                {result.symbol}
              </td>
              <td className="px-4 py-3 text-muted">{result.expiry_date}</td>
              <td className="px-4 py-3 text-muted">{result.classification}</td>
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
              <td className="px-4 py-3 text-muted">{result.candle_count}</td>
              <td className="px-4 py-3 text-muted">
                {formatDateTime(result.detected_at)}
              </td>
              <td className="px-4 py-3">
                <Link
                  href={`/dashboard/chart/${encodeURIComponent(result.symbol)}`}
                  className="text-xs text-accent hover:underline"
                >
                  Chart
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
