import { PageHeader } from "@/components/ui/PageHeader";
import { IntegrationPlaceholder } from "@/components/ui/States";

const ROLES = [
  {
    name: "SUPER_ADMIN",
    description:
      "Full platform access. Manages administrators, customers, roles, settings, audit logs and all operational controls.",
    permissions: ["All admin APIs", "Manage ADMIN accounts", "Audit logs", "System settings"],
  },
  {
    name: "ADMIN",
    description:
      "Operational administrator. Manages customers and market-data workflows, without SUPER_ADMIN-level account control.",
    permissions: ["Customer management", "Market data & scheduler", "Pipeline jobs", "No SUPER_ADMIN creation"],
  },
  {
    name: "CUSTOMER",
    description:
      "Scanner customer. Accesses permitted scanner results, charts, history and their own profile and sessions.",
    permissions: ["Dashboard and scanner", "Scan history", "Own profile & sessions", "No admin APIs"],
  },
];

export default function AdminRolesPage() {
  return (
    <>
      <PageHeader
        eyebrow="Customers"
        title="Roles & Permissions"
        description="Role catalog enforced centrally by FastAPI dependencies."
        breadcrumbs={[
          { href: "/admin", label: "Admin" },
          { href: "/admin/roles", label: "Roles" },
        ]}
      />
      <main className="space-y-5 p-4 sm:p-6 lg:p-8">
        <div className="grid gap-4 lg:grid-cols-3">
          {ROLES.map((role) => (
            <div key={role.name} className="rounded-2xl border border-white/[0.06] bg-card p-5">
              <p className="font-mono text-xs text-mint">{role.name}</p>
              <p className="mt-2 text-xs leading-relaxed text-mist">{role.description}</p>
              <ul className="mt-3 space-y-1 text-[11px] text-[#DCE4EE]">
                {role.permissions.map((permission) => (
                  <li key={permission}>· {permission}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <IntegrationPlaceholder
          title="Role management API not implemented"
          description="Roles are fixed by the backend. Creating custom roles or editing permission matrices requires a dedicated backend API; no fake role editor is shown."
          endpoints={[
            "GET /api/v1/admin/roles",
            "PATCH /api/v1/admin/roles/{role}",
            "GET /api/v1/admin/permissions",
          ]}
        />
      </main>
    </>
  );
}
