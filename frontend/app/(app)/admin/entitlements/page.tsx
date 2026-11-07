import Link from "next/link";

import { PageHeader } from "@/components/ui/PageHeader";
import { IntegrationPlaceholder } from "@/components/ui/States";

export default function Page() {
  return (
    <>
      <PageHeader
        eyebrow="Monetization"
        title="Entitlements"
        description="Plan feature matrices and user overrides require an entitlement API."
        breadcrumbs={[
          { href: "/admin", label: "Dashboard" },
          { href: "/admin/entitlements", label: "Entitlements" },
        ]}
        actions={
          <Link href="/admin" className="rounded-lg border border-white/10 px-3 py-1.5 text-xs hover:bg-white/5">
            Back
          </Link>
        }
      />
      <main className="p-4 sm:p-6 lg:p-8">
        <IntegrationPlaceholder
          title="Entitlements API not implemented"
          description="Plan feature matrices and user overrides require an entitlement API."
          endpoints={[
            "GET /api/v1/admin/features",
            "PATCH /api/v1/admin/features",
            "GET /api/v1/admin/entitlements"
          ]}
        />
      </main>
    </>
  );
}
