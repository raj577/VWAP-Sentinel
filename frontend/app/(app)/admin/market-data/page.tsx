export const dynamic = "force-dynamic";

import Link from "next/link";

import { PageHeader } from "@/components/ui/PageHeader";
import { MetricCard } from "@/components/ui/MetricCard";
import { Pagination } from "@/components/ui/Pagination";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ErrorState, EmptyState } from "@/components/ui/States";
import { ApiError } from "@/lib/api";
import { formatCount, formatDateTime } from "@/lib/format";
import { getInstruments, getMarketDataStatus } from "@/services/marketData";
import type { InstrumentPage, MarketDataStatus } from "@/types/api";

export default async function AdminMarketDataPage({
  searchParams,
}: {
  searchParams: Promise<{
    page?: string;
    q?: string;
    underlying?: string;
    status?: string;
    expiry?: string;
  }>;
}) {
  const params = await searchParams;
  const page = Math.max(1, Number(params.page ?? "1") || 1);
  const q = params.q?.trim() || undefined;
  const underlying = params.underlying?.trim() || undefined;
  const expiry = params.expiry?.trim() || undefined;
  const active =
    params.status === "active" ? true : params.status === "inactive" ? false : undefined;

  let status: MarketDataStatus | null = null;
  let instruments: InstrumentPage | null = null;
  let error: string | null = null;

  try {
    [status, instruments] = await Promise.all([
      getMarketDataStatus(),
      getInstruments({ page, pageSize: 50, q, underlying, expiry, active }),
    ]);
  } catch (caught) {
    error =
      caught instanceof ApiError
        ? `${caught.status}: ${caught.message}`
        : "The FastAPI backend is unreachable.";
  }

  const totalPages = instruments
    ? Math.max(1, Math.ceil(instruments.total / 50))
    : 1;
  const buildHref = (nextPage: number) => {
    const query = new URLSearchParams({ page: String(nextPage) });
    if (q) query.set("q", q);
    if (underlying) query.set("underlying", underlying);
    if (params.status) query.set("status", params.status);
    if (expiry) query.set("expiry", expiry);
    return `/admin/market-data?${query.toString()}`;
  };

  return (
    <>
      <PageHeader
        eyebrow="Market operations"
        title="Market Data"
        description="FYERS connection, stored futures contracts and candle coverage."
        breadcrumbs={[
          { href: "/admin", label: "Admin" },
          { href: "/admin/market-data", label: "Market Data" },
        ]}
        actions={
          <Link
            href="/admin/scheduler"
            className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-[#F5F7FA] hover:bg-white/5"
          >
            Refresh controls
          </Link>
        }
      />

      <main className="space-y-5 p-4 sm:p-6 lg:p-8">
        {error ? <ErrorState message={error} /> : null}

        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="FYERS connection"
            value={status?.fyers.status?.replaceAll("_", " ") ?? "Unknown"}
            hint={status?.fyers.message}
            unavailable={status?.fyers.status !== "CONNECTED"}
          />
          <MetricCard
            label="Active contracts"
            value={formatCount(status?.instruments_active)}
            hint={`${formatCount(status?.instruments_total)} stored`}
          />
          <MetricCard
            label="Stored candles"
            value={formatCount(status?.candles_total)}
            hint={`timeframe ${status?.timeframe ?? "60"} min`}
          />
          <MetricCard
            label="Latest candle"
            value={status?.latest_candle_at ? "Available" : "None"}
            hint={formatDateTime(status?.latest_candle_at)}
          />
        </section>

        <section className="rounded-2xl border border-white/[0.06] bg-card p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-sm font-semibold text-[#F5F7FA]">Latest ingestion</h2>
              <p className="text-xs text-mist">
                {status?.last_job
                  ? `Job #${status.last_job.id} · ${status.last_job.status} · ${formatDateTime(status.last_job.completed_at)}`
                  : "No ingestion job recorded."}
              </p>
            </div>
            <Link href="/admin/jobs" className="text-xs text-mint hover:underline">
              Pipeline jobs →
            </Link>
          </div>
        </section>

        <form className="grid gap-3 rounded-2xl border border-white/[0.06] bg-card p-4 sm:grid-cols-2 lg:grid-cols-5">
          <label className="text-[11px] text-mist">
            Search symbol / underlying
            <input
              name="q"
              defaultValue={q ?? ""}
              placeholder="RELIANCE"
              className="mt-1 w-full rounded-lg border border-white/10 bg-ink px-3 py-2 text-xs text-white"
            />
          </label>
          <label className="text-[11px] text-mist">
            Underlying
            <input
              name="underlying"
              defaultValue={underlying ?? ""}
              placeholder="NIFTY"
              className="mt-1 w-full rounded-lg border border-white/10 bg-ink px-3 py-2 text-xs text-white"
            />
          </label>
          <label className="text-[11px] text-mist">
            Status
            <select
              name="status"
              defaultValue={params.status ?? ""}
              className="mt-1 w-full rounded-lg border border-white/10 bg-ink px-3 py-2 text-xs text-white"
            >
              <option value="">All</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </label>
          <label className="text-[11px] text-mist">
            Expiry
            <input
              name="expiry"
              type="date"
              defaultValue={expiry ?? ""}
              className="mt-1 w-full rounded-lg border border-white/10 bg-ink px-3 py-2 text-xs text-white"
            />
          </label>
          <div className="flex items-end gap-2">
            <button
              type="submit"
              className="rounded-lg bg-mint px-3 py-2 text-xs font-medium text-[#04120b] hover:bg-[#3bf19c]"
            >
              Apply
            </button>
            <Link href="/admin/market-data" className="text-xs text-mist hover:text-white">
              Reset
            </Link>
          </div>
        </form>

        {instruments && instruments.items.length === 0 ? (
          <EmptyState
            title="No instruments match"
            description="Adjust the filters or run a market-data refresh."
            action={{ href: "/admin/scheduler", label: "Open scheduler" }}
          />
        ) : (
          <div className="overflow-x-auto rounded-2xl border border-white/[0.06] bg-card">
            <table className="min-w-[900px] w-full text-left text-xs">
              <thead className="border-b border-white/[0.06] text-[10px] uppercase tracking-wider text-mist">
                <tr>
                  <th className="px-4 py-3 font-medium">Symbol</th>
                  <th className="px-4 py-3 font-medium">Underlying</th>
                  <th className="px-4 py-3 font-medium">Expiry</th>
                  <th className="px-4 py-3 font-medium">Exchange</th>
                  <th className="px-4 py-3 font-medium">Type</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">First candle</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.05]">
                {(instruments?.items ?? []).map((instrument) => (
                  <tr key={instrument.id} className="hover:bg-white/[0.02]">
                    <td className="px-4 py-3 font-mono text-[#F5F7FA]">
                      {instrument.fyers_symbol}
                    </td>
                    <td className="px-4 py-3 text-mist">{instrument.underlying_symbol}</td>
                    <td className="px-4 py-3 text-mist">{instrument.expiry_date}</td>
                    <td className="px-4 py-3 text-mist">{instrument.exchange}</td>
                    <td className="px-4 py-3 text-mist">{instrument.instrument_type}</td>
                    <td className="px-4 py-3">
                      {instrument.is_active ? (
                        <StatusBadge status="ACTIVE" />
                      ) : (
                        <StatusBadge status="DISABLED" />
                      )}
                    </td>
                    <td className="px-4 py-3 text-mist">
                      {formatDateTime(instrument.first_available_timestamp)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex items-center justify-between gap-3">
          <p className="text-xs text-mist">
            {formatCount(instruments?.total)} contracts · page size 50
          </p>
          <Pagination page={page} totalPages={totalPages} buildHref={buildHref} />
        </div>

        <p className="text-[11px] text-mist/70">
          Last-candle timestamps per instrument are not exposed by the current
          instruments API; data freshness is shown at the dataset level above.
        </p>
      </main>
    </>
  );
}
