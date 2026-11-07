import Link from "next/link";

import { PageHeader } from "@/components/ui/PageHeader";
import { IntegrationPlaceholder } from "@/components/ui/States";

export default function Page() {
  return (
    <>
      <PageHeader
        eyebrow="Account"
        title="Billing"
        description="Payment history and invoices require a payment provider integration. No invoices are fabricated."
        breadcrumbs={[
          { href: "/dashboard", label: "Dashboard" },
          { href: "/dashboard/billing", label: "Billing" },
        ]}
        actions={
          <Link href="/dashboard" className="rounded-lg border border-white/10 px-3 py-1.5 text-xs hover:bg-white/5">
            Back
          </Link>
        }
      />
      <main className="p-4 sm:p-6 lg:p-8">
        <IntegrationPlaceholder
          title="Billing API not implemented"
          description="Payment history and invoices require a payment provider integration. No invoices are fabricated."
          endpoints={[
            "GET /api/v1/users/me/payments",
            "GET /api/v1/payments/{payment_id}"
          ]}
        />
      </main>
    </>
  );
}
