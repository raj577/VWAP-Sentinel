import Link from "next/link";

import { PageHeader } from "@/components/ui/PageHeader";
import { IntegrationPlaceholder } from "@/components/ui/States";

export default function Page() {
  return (
    <>
      <PageHeader
        eyebrow="Platform"
        title="Feature Flags"
        description="Global feature availability is part of the entitlement system, not yet implemented."
        breadcrumbs={[
          { href: "/admin", label: "Dashboard" },
          { href: "/admin/feature-flags", label: "Feature Flags" },
        ]}
        actions={
          <Link href="/admin" className="rounded-lg border border-white/10 px-3 py-1.5 text-xs hover:bg-white/5">
            Back
          </Link>
        }
      />
      <main className="p-4 sm:p-6 lg:p-8">
        <IntegrationPlaceholder
          title="Feature Flags API not implemented"
          description="Global feature availability is part of the entitlement system, not yet implemented."
          endpoints={[
            "GET /api/v1/admin/feature-flags",
            "PATCH /api/v1/admin/feature-flags/{key}"
          ]}
        />
      </main>
    </>
  );
}
