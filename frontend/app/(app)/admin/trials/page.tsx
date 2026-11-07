import Link from "next/link";

import { PageHeader } from "@/components/ui/PageHeader";
import { IntegrationPlaceholder } from "@/components/ui/States";

export default function Page() {
  return (
    <>
      <PageHeader
        eyebrow="Monetization"
        title="Trial Management"
        description="Trial settings and extension actions require a backend configuration API."
        breadcrumbs={[
          { href: "/admin", label: "Dashboard" },
          { href: "/admin/trial-management", label: "Trial Management" },
        ]}
        actions={
          <Link href="/admin" className="rounded-lg border border-white/10 px-3 py-1.5 text-xs hover:bg-white/5">
            Back
          </Link>
        }
      />
      <main className="p-4 sm:p-6 lg:p-8">
        <IntegrationPlaceholder
          title="Trial Management API not implemented"
          description="Trial settings and extension actions require a backend configuration API."
          endpoints={[
            "GET /api/v1/admin/trials/settings",
            "PATCH /api/v1/admin/trials/settings",
            "POST /api/v1/admin/users/{user_id}/extend-trial"
          ]}
        />
      </main>
    </>
  );
}
