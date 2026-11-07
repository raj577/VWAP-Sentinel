import { PageHeader } from "@/components/ui/PageHeader";
import { IntegrationPlaceholder } from "@/components/ui/States";

const MODULES = [
  {
    title: "Subscription plans",
    description:
      "Plan CRUD, pricing, billing intervals and plan feature configuration are not implemented in the backend yet. Historical plan references must be preserved when this lands.",
    endpoints: [
      "GET /api/v1/admin/plans",
      "POST /api/v1/admin/plans",
      "PATCH /api/v1/admin/plans/{plan_id}",
    ],
  },
  {
    title: "Trial management",
    description:
      "Trial duration, default trial plan, payment-method requirement, one-trial-per-user and expiry behaviour require a backend configuration API.",
    endpoints: [
      "GET /api/v1/admin/trials/settings",
      "PATCH /api/v1/admin/trials/settings",
      "POST /api/v1/admin/users/{user_id}/extend-trial",
    ],
  },
  {
    title: "Entitlements",
    description:
      "Plan feature matrix, global feature switches, usage limits and user overrides are not exposed by the backend yet. No mock switches are shown.",
    endpoints: [
      "GET /api/v1/admin/features",
      "PATCH /api/v1/admin/features",
      "GET /api/v1/admin/entitlements",
    ],
  },
  {
    title: "Payments",
    description:
      "Payment records and provider webhook history require a payment integration. Refund actions are intentionally absent until verified server-side support exists.",
    endpoints: [
      "GET /api/v1/admin/payments",
      "GET /api/v1/admin/payments/{payment_id}",
      "GET /api/v1/admin/payments/webhooks",
    ],
  },
  {
    title: "Feature flags",
    description:
      "Global feature availability is part of the entitlement system, which is not implemented yet. Changes will require audit logging.",
    endpoints: [
      "GET /api/v1/admin/feature-flags",
      "PATCH /api/v1/admin/feature-flags/{key}",
    ],
  },
];

export default function AdminMonetizationPlaceholderPage() {
  return (
    <>
      <PageHeader
        eyebrow="Monetization"
        title="Plans, Trials & Entitlements"
        description="This module is pending backend implementation. The UI shows the exact integration requirements instead of fabricated data."
        breadcrumbs={[
          { href: "/admin", label: "Admin" },
          { href: "/admin/plans", label: "Monetization" },
        ]}
      />
      <main className="grid gap-4 p-4 sm:p-6 lg:grid-cols-2 lg:p-8">
        {MODULES.map((module) => (
          <IntegrationPlaceholder
            key={module.title}
            title={module.title}
            description={module.description}
            endpoints={module.endpoints}
          />
        ))}
      </main>
    </>
  );
}
