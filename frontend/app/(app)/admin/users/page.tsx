export const dynamic = "force-dynamic";

import { PageHeader } from "@/components/ui/PageHeader";
import { ErrorState } from "@/components/ui/States";
import { UsersPanel } from "@/components/admin/UsersPanel";
import { ApiError } from "@/lib/api";
import { fetchCurrentUser } from "@/lib/serverAuth";
import { getAdminUsers } from "@/services/marketData";
import type { AdminUserPage } from "@/types/api";

export default async function AdminUsersPage() {
  const adminKey = process.env.ADMIN_API_KEY;
  const current = await fetchCurrentUser();
  const actorIsSuper = Boolean(current?.roles.includes("SUPER_ADMIN"));

  let users: AdminUserPage | null = null;
  let error: string | null = null;

  if (!adminKey) {
    error = "ADMIN_API_KEY is not configured.";
  } else {
    try {
      users = await getAdminUsers(adminKey, { pageSize: 20 });
    } catch (caught) {
      error =
        caught instanceof ApiError
          ? `${caught.status}: ${caught.message}`
          : "The FastAPI backend is unreachable.";
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Customers"
        title="Users"
        description="Search, filter and manage platform accounts. Actions are enforced by the backend role policy."
        breadcrumbs={[
          { href: "/admin", label: "Admin" },
          { href: "/admin/users", label: "Users" },
        ]}
      />
      <main className="space-y-5 p-4 sm:p-6 lg:p-8">
        {error ? <ErrorState message={error} /> : null}
        <UsersPanel initial={users} actorIsSuper={actorIsSuper} />
        <p className="text-[11px] text-mist/70">
          SUPER_ADMIN can manage ADMIN and CUSTOMER accounts. ADMIN can manage
          CUSTOMER accounts only. Nobody can change their own role here, and
          SUPER_ADMIN accounts cannot be modified through this screen.
        </p>
      </main>
    </>
  );
}
