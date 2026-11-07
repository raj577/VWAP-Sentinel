import Link from "next/link";

import { PageHeader } from "@/components/ui/PageHeader";
import { IntegrationPlaceholder } from "@/components/ui/States";

export default function Page() {
  return (
    <>
      <PageHeader
        eyebrow="Monetization"
        title="Payments"
        description="Payment records and webhook history require a payment integration."
        breadcrumbs={[
          { href: "/admin", label: "Dashboard" },
          { href: "/admin/payments", label: "Payments" },
        ]}
        actions={
          <Link href="/admin" className="rounded-lg border border-white/10 px-3 py-1.5 text-xs hover:bg-white/5">
            Back
          </Link>
        }
      />
      <main className="p-4 sm:p-6 lg:p-8">
        <IntegrationPlaceholder
          title="Payments API not implemented"
          description="Payment records and webhook history require a payment integration."
          endpoints={[
            "GET /api/v1/admin/payments",
            "GET /api/v1/admin/payments/{payment_id}",
            "GET /api/v1/admin/payments/webhooks"
          ]}
        />
      </main>
    </>
  );
}
