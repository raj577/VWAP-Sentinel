import Link from "next/link";

import { PageHeader } from "@/components/ui/PageHeader";
import { IntegrationPlaceholder } from "@/components/ui/States";

export default function Page() {
  return (
    <>
      <PageHeader
        eyebrow="Account"
        title="Subscription"
        description="Plan status, trial state, entitlements and usage limits require subscription APIs."
        breadcrumbs={[
          { href: "/dashboard", label: "Dashboard" },
          { href: "/dashboard/subscription", label: "Subscription" },
        ]}
        actions={
          <Link href="/dashboard" className="rounded-lg border border-white/10 px-3 py-1.5 text-xs hover:bg-white/5">
            Back
          </Link>
        }
      />
      <main className="p-4 sm:p-6 lg:p-8">
        <IntegrationPlaceholder
          title="Subscription API not implemented"
          description="Plan status, trial state, entitlements and usage limits require subscription APIs."
          endpoints={[
            "GET /api/v1/users/me/subscription",
            "GET /api/v1/users/me/features",
            "GET /api/v1/users/me/limits"
          ]}
        />
      </main>
    </>
  );
}
