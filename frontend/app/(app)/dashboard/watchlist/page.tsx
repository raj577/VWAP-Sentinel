import Link from "next/link";

import { PageHeader } from "@/components/ui/PageHeader";
import { IntegrationPlaceholder } from "@/components/ui/States";

export default function Page() {
  return (
    <>
      <PageHeader
        eyebrow="Account"
        title="Watchlist"
        description="Personal watchlists need backend persistence and plan-limit enforcement. No client-side fake persistence is provided."
        breadcrumbs={[
          { href: "/dashboard", label: "Dashboard" },
          { href: "/dashboard/watchlist", label: "Watchlist" },
        ]}
        actions={
          <Link href="/dashboard" className="rounded-lg border border-white/10 px-3 py-1.5 text-xs hover:bg-white/5">
            Back
          </Link>
        }
      />
      <main className="p-4 sm:p-6 lg:p-8">
        <IntegrationPlaceholder
          title="Watchlist API not implemented"
          description="Personal watchlists need backend persistence and plan-limit enforcement. No client-side fake persistence is provided."
          endpoints={[
            "GET /api/v1/watchlists",
            "POST /api/v1/watchlists",
            "POST /api/v1/watchlists/{id}/items",
            "DELETE /api/v1/watchlists/{id}/items/{item_id}"
          ]}
        />
      </main>
    </>
  );
}
