export const dynamic = "force-dynamic";

import { PageHeader } from "@/components/ui/PageHeader";
import { ErrorState } from "@/components/ui/States";
import { formatDateTime } from "@/lib/format";
import { fetchCurrentUser } from "@/lib/serverAuth";
import { getAuditLogs } from "@/services/marketData";
import type { AuditLogRow } from "@/types/api";

export default async function AdminAuditLogsPage() {
  const adminKey = process.env.ADMIN_API_KEY;
  const user = await fetchCurrentUser();
  const isSuper = Boolean(user?.roles.includes("SUPER_ADMIN"));

  let logs: AuditLogRow[] = [];
  let error: string | null = null;

  if (!isSuper) {
    error = "Only SUPER_ADMIN can read audit logs.";
  } else if (!adminKey) {
    error = "ADMIN_API_KEY is not configured.";
  } else {
    try {
      logs = await getAuditLogs(adminKey, 200);
    } catch {
      error = "Audit logs are unavailable.";
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Platform"
        title="Audit Logs"
        description="Security-sensitive actions recorded by the backend. Secrets and passwords never appear here."
        breadcrumbs={[
          { href: "/admin", label: "Admin" },
          { href: "/admin/audit-logs", label: "Audit Logs" },
        ]}
      />
      <main className="space-y-5 p-4 sm:p-6 lg:p-8">
        {error ? <ErrorState message={error} /> : null}

        {isSuper && !error ? (
          <>
            <div className="overflow-x-auto rounded-2xl border border-white/[0.06] bg-card">
              <table className="min-w-[900px] w-full text-left text-xs">
                <thead className="border-b border-white/[0.06] text-[10px] uppercase tracking-wider text-mist">
                  <tr>
                    <th className="px-4 py-3 font-medium">Action</th>
                    <th className="px-4 py-3 font-medium">Actor</th>
                    <th className="px-4 py-3 font-medium">Target</th>
                    <th className="px-4 py-3 font-medium">Entity</th>
                    <th className="px-4 py-3 font-medium">IP</th>
                    <th className="px-4 py-3 font-medium">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.05]">
                  {logs.map((row) => (
                    <tr key={row.id} className="hover:bg-white/[0.02]">
                      <td className="px-4 py-3 font-mono text-[#F5F7FA]">{row.action}</td>
                      <td className="px-4 py-3 font-mono text-mist">
                        {row.actor_user_id ? row.actor_user_id.slice(0, 8) : "system"}
                      </td>
                      <td className="px-4 py-3 font-mono text-mist">
                        {row.target_user_id ? row.target_user_id.slice(0, 8) : "—"}
                      </td>
                      <td className="px-4 py-3 text-mist">
                        {row.entity_type ?? "—"} {row.entity_id ?? ""}
                      </td>
                      <td className="px-4 py-3 text-mist">{row.ip_address ?? "—"}</td>
                      <td className="px-4 py-3 text-mist">{formatDateTime(row.created_at)}</td>
                    </tr>
                  ))}
                  {logs.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-6 text-mist">
                        No audit events recorded.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
            <p className="text-[11px] text-mist/70">
              The current audit API returns the most recent 200 events without
              server-side actor/action/date filters. Filtering and pagination
              require a backend extension.
            </p>
          </>
        ) : null}
      </main>
    </>
  );
}
