export const dynamic = "force-dynamic";

import Link from "next/link";

import { Header } from "@/components/Header";
import { ScanResultsTable } from "@/components/ScanResultsTable";
import { StatCard } from "@/components/StatCard";
import { ApiError } from "@/lib/api";
import { formatCount, formatDateTime } from "@/lib/format";
import { authHeaders } from "@/lib/serverAuth";
import { getScanComparison, getScanHistoryDetail } from "@/services/marketData";
import type { ScanComparison, ScanRunDetail } from "@/types/api";

export default async function ScanDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ runId: string }>;
  searchParams: Promise<{ compare_to?: string }>;
}) {
  const { runId } = await params;
  const { compare_to: compareToParam } = await searchParams;
  const numericRunId = Number(runId);

  let scan: ScanRunDetail | null = null;
  let comparison: ScanComparison | null = null;
  let error: string | null = null;

  if (!Number.isInteger(numericRunId) || numericRunId < 1) {
    error = "Invalid scan run id.";
  } else {
    try {
      const headers = await authHeaders();
      scan = await getScanHistoryDetail(numericRunId, headers);
    } catch (caught) {
      error =
        caught instanceof ApiError
          ? `${caught.status}: ${caught.message}`
          : "The FastAPI backend is unreachable.";
    }

    const compareTo = Number(compareToParam);
    if (
      scan &&
      Number.isInteger(compareTo) &&
      compareTo >= 1 &&
      compareTo !== numericRunId
    ) {
      try {
        comparison = await getScanComparison(
          numericRunId,
          compareTo,
          await authHeaders(),
        );
      } catch (caught) {
        if (!(caught instanceof ApiError && caught.status === 404)) {
          error =
            caught instanceof ApiError
              ? `${caught.status}: ${caught.message}`
              : "Could not compare scans.";
        }
      }
    }
  }

  return (
    <>
      <Header
        title={scan ? `Scan #${scan.id}` : "Scan details"}
        subtitle={
          scan
            ? `${scan.scan_type} · ${scan.status} · completed ${formatDateTime(
                scan.completed_at,
              )}`
            : "Immutable historical snapshot"
        }
      />

      <main className="flex-1 space-y-6 p-6">
        <Link href="/dashboard/history" className="text-xs text-muted hover:text-white">
          ← Previous scans
        </Link>

        {error ? (
          <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-4 text-sm text-amber-100">
            {error}
          </div>
        ) : null}

        {scan ? (
          <>
            <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <StatCard
                label="Contracts scanned"
                value={formatCount(scan.instruments_scanned)}
                hint={`${formatCount(scan.failed_instruments)} failed`}
              />
              <StatCard
                label="Matches"
                value={formatCount(scan.matches_count)}
                hint={`config ${scan.config_version}`}
              />
              <StatCard
                label="Completed"
                value={formatDateTime(scan.completed_at).split(",")[0]}
                hint={formatDateTime(scan.completed_at)}
              />
              <StatCard
                label="Data freshness"
                value={scan.data_freshness_at ? "Stored" : "Unknown"}
                hint={formatDateTime(scan.data_freshness_at)}
              />
            </section>

            <section className="rounded-lg border border-border bg-panel p-4">
              <form method="get" className="flex flex-wrap items-end gap-3 text-xs text-muted">
                <label className="flex flex-col gap-1">
                  Compare with run id
                  <input
                    name="compare_to"
                    type="number"
                    min={1}
                    defaultValue={compareToParam ?? ""}
                    placeholder="e.g. 12"
                    className="w-40 rounded-md border border-border bg-base px-3 py-2 text-xs text-white placeholder:text-muted"
                  />
                </label>
                <button
                  type="submit"
                  className="rounded-md border border-border px-3 py-2 text-xs text-white hover:bg-white/5"
                >
                  Compare
                </button>
                <Link href={`/dashboard/history/${scan.id}`} className="text-xs text-muted hover:text-white">
                  Clear
                </Link>
              </form>

              {comparison ? (
                <div className="mt-4 grid gap-3 text-xs sm:grid-cols-3">
                  <div>
                    <p className="text-muted">Appeared in #{comparison.compare_run_id}</p>
                    <p className="mt-1 font-mono text-emerald-300">
                      {comparison.appeared.length
                        ? comparison.appeared.join(", ")
                        : "none"}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted">Disappeared since #{comparison.compare_run_id}</p>
                    <p className="mt-1 font-mono text-red-300">
                      {comparison.disappeared.length
                        ? comparison.disappeared.join(", ")
                        : "none"}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted">Persisted</p>
                    <p className="mt-1 font-mono text-muted">
                      {comparison.persisted.length
                        ? comparison.persisted.join(", ")
                        : "none"}
                    </p>
                  </div>
                </div>
              ) : null}
            </section>

            <section className="space-y-3">
              <h2 className="text-sm font-semibold text-white">Results</h2>
              <ScanResultsTable results={scan.results} />
            </section>
          </>
        ) : null}
      </main>
    </>
  );
}
