"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { MetricCard } from "@/components/ui/MetricCard";
import { formatDateTime, formatNumber } from "@/lib/format";
import type { ScanRunDetail } from "@/types/api";

const PATTERN_TONES: Record<string, "mint" | "sky" | "amber" | "neutral"> = {
  "AVWAP TOUCH": "sky",
  "AVWAP HUGGING": "mint",
  "AVWAP CONSOLIDATION": "amber",
  "AVWAP RECLAIM": "mint",
};

export function ScannerWorkspace({ scan }: { scan: ScanRunDetail | null }) {
  const [search, setSearch] = useState("");
  const [pattern, setPattern] = useState("");
  const [expiry, setExpiry] = useState("");
  const [sort, setSort] = useState<"distance" | "distance-desc" | "candles">("distance");
  const [page, setPage] = useState(1);
  const pageSize = 12;

  const results = scan?.results ?? [];
  const patterns = Array.from(new Set(results.map((row) => row.classification))).sort();
  const expiries = Array.from(new Set(results.map((row) => row.expiry_date))).sort();

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    const rows = results.filter((row) => {
      if (needle && !row.symbol.toLowerCase().includes(needle)) return false;
      if (pattern && row.classification !== pattern) return false;
      if (expiry && row.expiry_date !== expiry) return false;
      return true;
    });
    rows.sort((a, b) => {
      if (sort === "distance") return Math.abs(a.distance_pct) - Math.abs(b.distance_pct);
      if (sort === "distance-desc") return Math.abs(b.distance_pct) - Math.abs(a.distance_pct);
      return b.candle_count - a.candle_count;
    });
    return rows;
  }, [results, search, pattern, expiry, sort]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const safePage = Math.min(page, totalPages);
  const visible = filtered.slice((safePage - 1) * pageSize, safePage * pageSize);

  const counts = {
    touch: results.filter((row) => row.classification === "AVWAP TOUCH").length,
    hugging: results.filter((row) => row.classification === "AVWAP HUGGING").length,
    consolidation: results.filter((row) => row.classification === "AVWAP CONSOLIDATION").length,
    reclaim: results.filter((row) => row.classification === "AVWAP RECLAIM").length,
  };

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <MetricCard
          label="Matching futures"
          value={results.length}
          hint={scan ? `Scan #${scan.id}` : "No scan"}
        />
        <MetricCard label="AVWAP Touch" value={counts.touch} />
        <MetricCard label="AVWAP Hugging" value={counts.hugging} />
        <MetricCard label="Consolidation" value={counts.consolidation} />
        <MetricCard label="Reclaim" value={counts.reclaim} />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-white/[0.06] bg-card px-4 py-3">
        <p className="text-xs text-mist">
          {scan
            ? `Latest completed scan #${scan.id} · ${formatDateTime(scan.completed_at)} · config ${scan.config_version}`
            : "No completed scan available."}
        </p>
        {scan ? (
          <p className="text-[11px] text-mist/70">
            Snapshot data, not live streaming prices.
          </p>
        ) : null}
      </div>

      <div className="grid gap-3 rounded-2xl border border-white/[0.06] bg-card p-4 sm:grid-cols-2 lg:grid-cols-5">
        <label className="text-[11px] text-mist">
          Search symbol
          <input
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
            }}
            placeholder="RELIANCE"
            className="mt-1 w-full rounded-lg border border-white/10 bg-ink px-3 py-2 text-xs text-white"
          />
        </label>
        <label className="text-[11px] text-mist">
          Pattern
          <select
            value={pattern}
            onChange={(event) => {
              setPattern(event.target.value);
              setPage(1);
            }}
            className="mt-1 w-full rounded-lg border border-white/10 bg-ink px-3 py-2 text-xs text-white"
          >
            <option value="">All patterns</option>
            {patterns.map((value) => (
              <option key={value} value={value}>{value}</option>
            ))}
          </select>
        </label>
        <label className="text-[11px] text-mist">
          Expiry
          <select
            value={expiry}
            onChange={(event) => {
              setExpiry(event.target.value);
              setPage(1);
            }}
            className="mt-1 w-full rounded-lg border border-white/10 bg-ink px-3 py-2 text-xs text-white"
          >
            <option value="">All expiries</option>
            {expiries.map((value) => (
              <option key={value} value={value}>{value}</option>
            ))}
          </select>
        </label>
        <label className="text-[11px] text-mist">
          Sort
          <select
            value={sort}
            onChange={(event) => setSort(event.target.value as typeof sort)}
            className="mt-1 w-full rounded-lg border border-white/10 bg-ink px-3 py-2 text-xs text-white"
          >
            <option value="distance">Closest to AVWAP</option>
            <option value="distance-desc">Farthest from AVWAP</option>
            <option value="candles">Most candles</option>
          </select>
        </label>
        <div className="flex items-end justify-between text-xs text-mist">
          <span>{filtered.length} matches</span>
          <div className="flex gap-1">
            <button
              type="button"
              disabled={safePage <= 1}
              onClick={() => setPage((value) => Math.max(1, value - 1))}
              className="rounded border border-white/10 px-2 py-1 disabled:opacity-40"
            >
              Prev
            </button>
            <button
              type="button"
              disabled={safePage >= totalPages}
              onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
              className="rounded border border-white/10 px-2 py-1 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-white/[0.06] bg-card">
        <table className="min-w-[1000px] w-full text-left text-xs">
          <thead className="border-b border-white/[0.06] text-[10px] uppercase tracking-wider text-mist">
            <tr>
              <th className="px-4 py-3 font-medium">Symbol</th>
              <th className="px-4 py-3 font-medium">Expiry</th>
              <th className="px-4 py-3 font-medium">Last price</th>
              <th className="px-4 py-3 font-medium">Contract AVWAP</th>
              <th className="px-4 py-3 font-medium">Session VWAP</th>
              <th className="px-4 py-3 font-medium">Distance</th>
              <th className="px-4 py-3 font-medium">Candles</th>
              <th className="px-4 py-3 font-medium">Pattern</th>
              <th className="px-4 py-3 font-medium">Scan time</th>
              <th className="px-4 py-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.05]">
            {visible.map((row) => (
              <tr key={row.id} className="hover:bg-white/[0.02]">
                <td className="px-4 py-3 font-mono text-[#F5F7FA]">{row.symbol}</td>
                <td className="px-4 py-3 text-mist">{row.expiry_date}</td>
                <td className="px-4 py-3 font-mono text-[#DCE4EE]">{formatNumber(row.last_price)}</td>
                <td className="px-4 py-3 font-mono text-mist">{formatNumber(row.avwap)}</td>
                <td className="px-4 py-3 font-mono text-mist">{formatNumber(row.session_vwap)}</td>
                <td className={`px-4 py-3 font-mono ${row.distance_pct < 0 ? "text-red-300" : "text-mint"}`}>
                  {formatNumber(row.distance_pct, 3)}%
                </td>
                <td className="px-4 py-3 font-mono text-mist">{row.candle_count}</td>
                <td className="px-4 py-3">
                  <Badge tone={PATTERN_TONES[row.classification] ?? "neutral"}>
                    {row.classification}
                  </Badge>
                </td>
                <td className="px-4 py-3 text-mist">{formatDateTime(row.detected_at)}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <Link href={`/dashboard/scanner/${encodeURIComponent(row.symbol)}`} className="text-mint hover:underline">
                      Details
                    </Link>
                    <Link href={`/dashboard/chart/${encodeURIComponent(row.symbol)}`} className="text-sky hover:underline">
                      Chart
                    </Link>
                    <span className="cursor-not-allowed text-[10px] text-mist/50" title="Watchlist API not implemented">
                      Watchlist
                    </span>
                  </div>
                </td>
              </tr>
            ))}
            {scan && visible.length === 0 ? (
              <tr>
                <td colSpan={10} className="px-4 py-6 text-mist">
                  No matches for these filters.
                </td>
              </tr>
            ) : null}
            {!scan ? (
              <tr>
                <td colSpan={10} className="px-4 py-6 text-mist">
                  No completed scan is available yet.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-xs text-mist">
        <p>Page {safePage} of {totalPages} · {filtered.length} filtered</p>
        <p className="text-mist/60">Watchlist actions require a backend API.</p>
      </div>
    </div>
  );
}
