export const dynamic = "force-dynamic";

import Link from "next/link";

import { Header } from "@/components/Header";
import { ApiError } from "@/lib/api";
import { formatCount, formatDateTime } from "@/lib/format";
import { authHeaders } from "@/lib/serverAuth";
import { getScanHistory } from "@/services/marketData";
import type { ScanRunPage } from "@/types/api";

export default async function PreviousScansPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; symbol?: string; classification?: string }>;
}) {
  const params = await searchParams;
  const page = Math.max(1, Number(params.page ?? "1") || 1);
  const symbol = params.symbol?.trim() || undefined;
  const classification = params.classification?.trim() || undefined;

  let history: ScanRunPage | null = null;
  let error: string | null = null;

  try {
    history = await getScanHistory(
      {
        page,
        pageSize: 20,
        symbol,
        classification,
      },
      await authHeaders(),
    );
  } catch (caught) {
    error =
      caught instanceof ApiError
        ? `${caught.status}: ${caught.message}`
        : "The FastAPI backend is unreachable.";
  }

  const totalPages = history ? Math.max(1, Math.ceil(history.total / 20)) : 1;
  const query = (nextPage: number) => {
    const search = new URLSearchParams({ page: String(nextPage) });
    if (symbol) search.set("symbol", symbol);
    if (classification) search.set("classification", classification);
    return `/dashboard/history?${search.toString()}`;
  };

  return (
    <>
      <Header
        title="Scan History"
        subtitle="Immutable scan snapshots with match history"
      />

      <main className="flex-1 space-y-6 p-6">
        <form className="flex flex-wrap items-end gap-3 rounded-lg border border-border bg-panel p-4 text-xs text-muted">
          <label className="flex flex-col gap-1">
            Symbol
            <input
              name="symbol"
              defaultValue={symbol ?? ""}
              placeholder="NSE:RELIANCE26NOVFUT"
              className="w-64 rounded-md border border-border bg-base px-3 py-2 font-mono text-xs text-white placeholder:text-muted"
            />
          </label>
          <label className="flex flex-col gap-1">
            Classification
            <input
              name="classification"
              defaultValue={classification ?? ""}
              placeholder="AVWAP HUGGING"
              className="w-56 rounded-md border border-border bg-base px-3 py-2 text-xs text-white placeholder:text-muted"
            />
          </label>
          <button
            type="submit"
            className="rounded-md border border-border px-3 py-2 text-xs text-white hover:bg-white/5"
          >
            Filter
          </button>
          <Link href="/dashboard/history" className="text-xs text-muted hover:text-white">
            Reset
          </Link>
        </form>

        {error ? (
          <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-4 text-sm text-amber-100">
            {error}
          </div>
        ) : null}

        <div className="overflow-x-auto rounded-lg border border-border bg-panel">
          <table className="min-w-full divide-y divide-border text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-muted">
              <tr>
                <th className="px-4 py-3">Run</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Scanned</th>
                <th className="px-4 py-3">Matches</th>
                <th className="px-4 py-3">Failed</th>
                <th className="px-4 py-3">Completed</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {(history?.items ?? []).map((run) => (
                <tr key={run.id} className="hover:bg-white/[0.02]">
                  <td className="px-4 py-3 font-mono text-xs text-white">
                    #{run.id}
                  </td>
                  <td className="px-4 py-3 text-muted">{run.scan_type}</td>
                  <td className="px-4 py-3 text-muted">{run.status}</td>
                  <td className="px-4 py-3 text-muted">
                    {formatCount(run.instruments_scanned)}
                  </td>
                  <td className="px-4 py-3 text-muted">
                    {formatCount(run.matches_count)}
                  </td>
                  <td className="px-4 py-3 text-muted">
                    {formatCount(run.failed_instruments)}
                  </td>
                  <td className="px-4 py-3 text-muted">
                    {formatDateTime(run.completed_at)}
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/dashboard/history/${run.id}`}
                      className="text-xs text-accent hover:underline"
                    >
                      Details
                    </Link>
                  </td>
                </tr>
              ))}
              {history && history.items.length === 0 ? (
                <tr>
                  <td className="px-4 py-6 text-muted" colSpan={8}>
                    No scan runs match this filter.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between text-xs text-muted">
          <span>
            Page {history?.page ?? page} of {totalPages} ·{" "}
            {formatCount(history?.total)} runs
          </span>
          <div className="flex gap-3">
            {page > 1 ? (
              <Link href={query(page - 1)} className="hover:text-white">
                ← Newer
              </Link>
            ) : null}
            {page < totalPages ? (
              <Link href={query(page + 1)} className="hover:text-white">
                Older →
              </Link>
            ) : null}
          </div>
        </div>
      </main>
    </>
  );
}
