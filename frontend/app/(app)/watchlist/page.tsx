import { Header } from "@/components/Header";

export default function WatchlistPage() {
  return (
    <>
      <Header title="Watchlist" subtitle="Customer watchlists arrive after auth" />
      <main className="flex-1 p-6">
        <div className="rounded-lg border border-border bg-panel p-6 text-sm text-muted">
          Watchlists are part of the customer dashboard phase. The database
          schema is planned in docs/SAAS_PLAN.md.
        </div>
      </main>
    </>
  );
}
