import Link from "next/link";

import { PageHeader } from "@/components/ui/PageHeader";
import { IntegrationPlaceholder } from "@/components/ui/States";

export default function Page() {
  return (
    <>
      <PageHeader
        eyebrow="Account"
        title="Strategies & Education"
        description="Admin-published guides and strategy presets require a content API. Draft content is never presented as official."
        breadcrumbs={[
          { href: "/dashboard", label: "Dashboard" },
          { href: "/dashboard/strategies-&-education", label: "Strategies & Education" },
        ]}
        actions={
          <Link href="/dashboard" className="rounded-lg border border-white/10 px-3 py-1.5 text-xs hover:bg-white/5">
            Back
          </Link>
        }
      />
      <main className="p-4 sm:p-6 lg:p-8">
        <IntegrationPlaceholder
          title="Strategies & Education API not implemented"
          description="Admin-published guides and strategy presets require a content API. Draft content is never presented as official."
          endpoints={[
            "GET /api/v1/strategies",
            "GET /api/v1/guides",
            "POST /api/v1/admin/guides"
          ]}
        />
      </main>
    </>
  );
}
