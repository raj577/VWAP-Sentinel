export const dynamic = "force-dynamic";

import { Header } from "@/components/Header";
import { ProfileForm } from "@/components/ProfileForm";
import { formatDateTime } from "@/lib/format";
import { requireUser } from "@/lib/serverAuth";

export default async function ProfilePage() {
  const user = await requireUser();

  return (
    <>
      <Header title="Profile" subtitle="Account details and display name" />
      <main className="flex-1 space-y-6 p-6">
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-lg border border-border bg-panel p-4">
            <p className="text-xs uppercase tracking-wide text-muted">Email</p>
            <p className="mt-2 text-sm text-white">{user.email}</p>
          </div>
          <div className="rounded-lg border border-border bg-panel p-4">
            <p className="text-xs uppercase tracking-wide text-muted">Status</p>
            <p className="mt-2 text-sm text-white">{user.account_status}</p>
          </div>
          <div className="rounded-lg border border-border bg-panel p-4">
            <p className="text-xs uppercase tracking-wide text-muted">Roles</p>
            <p className="mt-2 text-sm text-white">{user.roles.join(", ")}</p>
          </div>
          <div className="rounded-lg border border-border bg-panel p-4">
            <p className="text-xs uppercase tracking-wide text-muted">Created</p>
            <p className="mt-2 text-sm text-white">
              {formatDateTime(user.created_at)}
            </p>
          </div>
        </section>

        <section className="rounded-lg border border-border bg-panel p-4">
          <h2 className="mb-3 text-sm font-semibold text-white">
            Display name
          </h2>
          <ProfileForm initialName={user.full_name} />
        </section>

        <p className="text-xs text-muted">
          Email changes and billing details are managed in later phases.
        </p>
      </main>
    </>
  );
}
