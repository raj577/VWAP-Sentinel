import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";

const ROWS = [
  { symbol: "MARICO", price: "612.40", avwap: "611.85", distance: "+0.09%", pattern: "AVWAP TOUCH", candles: 1, tone: "sky" as const },
  { symbol: "RELIANCE", price: "1,469.00", avwap: "1,466.70", distance: "+0.16%", pattern: "AVWAP HUGGING", candles: 3, tone: "mint" as const },
  { symbol: "TATAMOTORS", price: "742.15", avwap: "739.90", distance: "+0.30%", pattern: "AVWAP CONSOLIDATION", candles: 4, tone: "amber" as const },
  { symbol: "SBIN", price: "812.60", avwap: "814.20", distance: "-0.20%", pattern: "AVWAP TOUCH", candles: 2, tone: "sky" as const },
  { symbol: "HDFCBANK", price: "1,688.50", avwap: "1,681.90", distance: "+0.39%", pattern: "AVWAP RECLAIM", candles: 2, tone: "mint" as const },
];

export function ScannerPreview() {
  return (
    <section id="scanner-preview" className="relative scroll-mt-24 py-20 sm:py-24">
      <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-mint">
              Scanner
            </p>
            <h2 className="mt-3 text-3xl font-semibold tracking-[-0.02em] text-[#F5F7FA] sm:text-4xl">
              One Scan. Every Active Contract.
            </h2>
            <p className="mt-4 text-[15px] leading-relaxed text-mist">
              Results are ranked by absolute distance from contract AVWAP, with
              candle structure and pattern classification attached to each
              match.
            </p>
          </div>
          <Badge tone="neutral" className="self-start sm:self-auto">
            Data freshness shown in the app
          </Badge>
        </div>

        <Card className="mt-10 overflow-hidden p-0">
          <div className="flex items-center justify-between border-b border-white/[0.08] px-4 py-3 sm:px-6">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-mint" />
              <span className="text-xs text-mist">Latest completed scan</span>
            </div>
            <span className="font-mono text-[11px] text-mist/70">
              1H · NSE FUTURES
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-[760px] w-full text-left text-sm">
              <thead className="bg-white/[0.02] text-[11px] uppercase tracking-wider text-mist">
                <tr>
                  <th className="px-4 py-3 font-medium sm:px-6">Symbol</th>
                  <th className="px-4 py-3 font-medium">Last Price</th>
                  <th className="px-4 py-3 font-medium">Contract AVWAP</th>
                  <th className="px-4 py-3 font-medium">Distance %</th>
                  <th className="px-4 py-3 font-medium">Pattern</th>
                  <th className="px-4 py-3 font-medium sm:px-6">Candles</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.06]">
                {ROWS.map((row) => (
                  <tr key={row.symbol} className="transition-colors hover:bg-white/[0.025]">
                    <td className="px-4 py-3.5 font-mono text-[12px] text-[#F5F7FA] sm:px-6">
                      {row.symbol}
                    </td>
                    <td className="px-4 py-3.5 font-mono text-[12px] text-[#DCE4EE]">
                      {row.price}
                    </td>
                    <td className="px-4 py-3.5 font-mono text-[12px] text-mist">
                      {row.avwap}
                    </td>
                    <td
                      className={`px-4 py-3.5 font-mono text-[12px] ${
                        row.distance.startsWith("-") ? "text-red-300" : "text-mint"
                      }`}
                    >
                      {row.distance}
                    </td>
                    <td className="px-4 py-3.5">
                      <Badge tone={row.tone}>{row.pattern}</Badge>
                    </td>
                    <td className="px-4 py-3.5 font-mono text-[12px] text-mist sm:px-6">
                      {row.candles}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="border-t border-white/[0.08] px-4 py-3 text-[11px] text-mist/70 sm:px-6">
            Illustrative scanner preview — not live market data.
          </div>
        </Card>
      </div>
    </section>
  );
}
