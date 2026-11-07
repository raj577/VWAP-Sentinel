"use client";

import { Fragment, useCallback, useEffect, useState } from "react";

import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatDateTime } from "@/lib/format";
import type { AdminUserPage } from "@/types/api";

const ROLE_OPTIONS = ["", "SUPER_ADMIN", "ADMIN", "CUSTOMER"];
const STATUS_OPTIONS = ["", "ACTIVE", "PENDING_VERIFICATION", "SUSPENDED", "DISABLED"];

export function UsersPanel({
  initial,
  actorIsSuper,
}: {
  initial: AdminUserPage | null;
  actorIsSuper: boolean;
}) {
  const [data, setData] = useState<AdminUserPage | null>(initial);
  const [page, setPage] = useState(initial?.page ?? 1);
  const [search, setSearch] = useState("");
  const [role, setRole] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  const load = useCallback(async () => {
    const query = new URLSearchParams({
      page: String(page),
      page_size: "20",
    });
    if (search.trim()) query.set("search", search.trim());
    if (role) query.set("role", role);
    if (status) query.set("account_status", status);
    try {
      const response = await fetch(`/api/admin/users?${query}`, {
        cache: "no-store",
      });
      if (!response.ok) {
        setError("Could not load users.");
        return;
      }
      setData((await response.json()) as AdminUserPage);
      setError(null);
    } catch {
      setError("The backend is unreachable.");
    }
  }, [page, search, role, status]);

  useEffect(() => {
    void load();
  }, [load]);

  async function action(path: string, method: "PATCH" | "POST", body?: unknown) {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`/api/admin${path}`, {
        method,
        headers: body ? { "Content-Type": "application/json" } : undefined,
        body: body ? JSON.stringify(body) : undefined,
        cache: "no-store",
      });
      if (!response.ok) {
        let detail = `Request failed (${response.status})`;
        try {
          const payload = (await response.json()) as { detail?: unknown };
          if (typeof payload.detail === "string") detail = payload.detail;
        } catch {
          // ignore
        }
        setError(detail);
        return;
      }
      await load();
    } catch {
      setError("The backend is unreachable.");
    } finally {
      setBusy(false);
    }
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total / 20)) : 1;

  return (
    <div className="space-y-4">
      <div className="grid gap-3 rounded-2xl border border-white/[0.06] bg-card p-4 sm:grid-cols-2 lg:grid-cols-4">
        <label className="text-[11px] text-mist">
          Search name or email
          <input
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
            }}
            placeholder="customer@example.com"
            className="mt-1 w-full rounded-lg border border-white/10 bg-ink px-3 py-2 text-xs text-white"
          />
        </label>
        <label className="text-[11px] text-mist">
          Role
          <select
            value={role}
            onChange={(event) => {
              setRole(event.target.value);
              setPage(1);
            }}
            className="mt-1 w-full rounded-lg border border-white/10 bg-ink px-3 py-2 text-xs text-white"
          >
            {ROLE_OPTIONS.map((option) => (
              <option key={option || "all"} value={option}>
                {option || "All roles"}
              </option>
            ))}
          </select>
        </label>
        <label className="text-[11px] text-mist">
          Status
          <select
            value={status}
            onChange={(event) => {
              setStatus(event.target.value);
              setPage(1);
            }}
            className="mt-1 w-full rounded-lg border border-white/10 bg-ink px-3 py-2 text-xs text-white"
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option || "all"} value={option}>
                {option.replaceAll("_", " ") || "All statuses"}
              </option>
            ))}
          </select>
        </label>
        <div className="flex items-end justify-between gap-2 text-xs text-mist">
          <span>{data?.total ?? 0} users</span>
          <div className="flex gap-1">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((value) => Math.max(1, value - 1))}
              className="rounded border border-white/10 px-2 py-1 disabled:opacity-40"
            >
              Prev
            </button>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
              className="rounded border border-white/10 px-2 py-1 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      </div>

      {error ? <p className="text-xs text-red-300">{error}</p> : null}

      <div className="overflow-x-auto rounded-2xl border border-white/[0.06] bg-card">
        <table className="min-w-[1000px] w-full text-left text-xs">
          <thead className="border-b border-white/[0.06] text-[10px] uppercase tracking-wider text-mist">
            <tr>
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Email</th>
              <th className="px-4 py-3 font-medium">Role</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Subscription</th>
              <th className="px-4 py-3 font-medium">Registered</th>
              <th className="px-4 py-3 font-medium">Last login</th>
              <th className="px-4 py-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.05]">
            {(data?.items ?? []).map((account) => {
              const isSuper = account.roles.includes("SUPER_ADMIN");
              const isAdmin = account.roles.includes("ADMIN");
              const protectedTarget = isSuper || (isAdmin && !actorIsSuper);
              return (
                <>
                  <tr key={account.id} className="hover:bg-white/[0.02]">
                    <td className="px-4 py-3 text-[#DCE4EE]">{account.full_name}</td>
                    <td className="px-4 py-3 text-mist">{account.email}</td>
                    <td className="px-4 py-3 text-mist">{account.roles.join(", ")}</td>
                    <td className="px-4 py-3"><StatusBadge status={account.account_status} /></td>
                    <td className="px-4 py-3 text-mist">Not available</td>
                    <td className="px-4 py-3 text-mist">{formatDateTime(account.created_at)}</td>
                    <td className="px-4 py-3 text-mist">{formatDateTime(account.last_login_at)}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <button
                          type="button"
                          onClick={() => setExpanded(expanded === account.id ? null : account.id)}
                          className="text-mint hover:underline"
                        >
                          {expanded === account.id ? "Hide" : "Details"}
                        </button>
                        {!protectedTarget ? (
                          <>
                            {account.account_status === "ACTIVE" ? (
                              <button
                                type="button"
                                disabled={busy}
                                onClick={() => {
                                  if (window.confirm(`Suspend ${account.email}?`)) {
                                    void action(`/users/${account.id}/status`, "PATCH", {
                                      account_status: "SUSPENDED",
                                    });
                                  }
                                }}
                                className="text-red-300 hover:underline disabled:opacity-50"
                              >
                                Suspend
                              </button>
                            ) : (
                              <button
                                type="button"
                                disabled={busy}
                                onClick={() => {
                                  if (window.confirm(`Reactivate ${account.email}?`)) {
                                    void action(`/users/${account.id}/status`, "PATCH", {
                                      account_status: "ACTIVE",
                                    });
                                  }
                                }}
                                className="text-mint hover:underline disabled:opacity-50"
                              >
                                Reactivate
                              </button>
                            )}
                            {actorIsSuper && account.roles.includes("ADMIN") ? (
                              <button
                                type="button"
                                disabled={busy}
                                onClick={() => {
                                  if (window.confirm(`Change ${account.email} to CUSTOMER?`)) {
                                    void action(`/users/${account.id}/role`, "PATCH", {
                                      role: "CUSTOMER",
                                    });
                                  }
                                }}
                                className="text-amber-300 hover:underline disabled:opacity-50"
                              >
                                Make customer
                              </button>
                            ) : null}
                            {actorIsSuper && !account.roles.includes("ADMIN") ? (
                              <button
                                type="button"
                                disabled={busy}
                                onClick={() => {
                                  if (window.confirm(`Promote ${account.email} to ADMIN?`)) {
                                    void action(`/users/${account.id}/role`, "PATCH", {
                                      role: "ADMIN",
                                    });
                                  }
                                }}
                                className="text-sky hover:underline disabled:opacity-50"
                              >
                                Make admin
                              </button>
                            ) : null}
                            <button
                              type="button"
                              disabled={busy}
                              onClick={() => {
                                if (window.confirm(`Revoke all sessions for ${account.email}?`)) {
                                  void action(`/users/${account.id}/revoke-sessions`, "POST");
                                }
                              }}
                              className="text-amber-300 hover:underline disabled:opacity-50"
                            >
                              Revoke sessions
                            </button>
                          </>
                        ) : (
                          <span className="text-[10px] text-mist">Protected</span>
                        )}
                      </div>
                    </td>
                  </tr>
                  {expanded === account.id ? (
                    <tr key={`${account.id}-detail`}>
                      <td colSpan={8} className="bg-ink/40 px-4 py-3 text-mist">
                        <div className="grid gap-2 sm:grid-cols-3">
                          <p>ID: <span className="font-mono text-[#DCE4EE]">{account.id}</span></p>
                          <p>Email verified: {formatDateTime(account.email_verified_at)}</p>
                          <p>Account status: {account.account_status}</p>
                        </div>
                        <p className="mt-2 text-[11px]">
                          Subscription and session-detail APIs are not implemented yet; session
                          revocation is available.
                        </p>
                      </td>
                    </tr>
                  ) : null}
                </>
              );
            })}
            {data && data.items.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-4 py-6 text-mist">
                  No users match these filters.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}
