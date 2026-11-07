"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { formatDateTime } from "@/lib/format";
import {
  AuthApiError,
  changePassword,
  fetchSessions,
  logoutAll,
  revokeSession,
} from "@/services/auth";
import type { AuthSession } from "@/types/auth";

export function SessionsPanel() {
  const router = useRouter();
  const [sessions, setSessions] = useState<AuthSession[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const response = await fetchSessions();
      setSessions(response.sessions);
    } catch (caught) {
      setError(
        caught instanceof AuthApiError
          ? caught.message
          : "Could not load sessions.",
      );
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function revoke(id: string) {
    setError(null);
    try {
      await revokeSession(id);
      await load();
    } catch (caught) {
      setError(
        caught instanceof AuthApiError
          ? caught.message
          : "Could not revoke session.",
      );
    }
  }

  async function signOutAll() {
    if (!window.confirm("Sign out from every device?")) return;
    try {
      await logoutAll();
      router.push("/login");
      router.refresh();
    } catch (caught) {
      setError(
        caught instanceof AuthApiError ? caught.message : "Logout failed.",
      );
    }
  }

  async function submitPassword(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const response = await changePassword({
        current_password: current,
        new_password: next,
      });
      setMessage(response.message);
      setCurrent("");
      setNext("");
      await load();
    } catch (caught) {
      setError(
        caught instanceof AuthApiError
          ? caught.message
          : "Password change failed.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-8">
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">Active sessions</h2>
          <button
            type="button"
            onClick={() => void signOutAll()}
            className="rounded-md border border-red-500/40 px-3 py-1.5 text-xs text-red-300 hover:bg-red-500/10"
          >
            Sign out from all devices
          </button>
        </div>
        <div className="overflow-x-auto rounded-lg border border-border bg-panel">
          <table className="min-w-full divide-y divide-border text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-muted">
              <tr>
                <th className="px-4 py-3">Device</th>
                <th className="px-4 py-3">IP</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3">Last activity</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {sessions.map((session) => (
                <tr key={session.id}>
                  <td className="px-4 py-3 text-xs text-white">
                    {session.device_name ?? "Unknown device"}
                    {session.current ? (
                      <span className="ml-2 rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] text-emerald-300">
                        this session
                      </span>
                    ) : null}
                  </td>
                  <td className="px-4 py-3 text-xs text-muted">
                    {session.ip_address ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-xs text-muted">
                    {formatDateTime(session.created_at)}
                  </td>
                  <td className="px-4 py-3 text-xs text-muted">
                    {formatDateTime(session.last_activity_at)}
                  </td>
                  <td className="px-4 py-3">
                    {!session.current ? (
                      <button
                        type="button"
                        onClick={() => void revoke(session.id)}
                        className="text-xs text-red-300 hover:underline"
                      >
                        Revoke
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
              {sessions.length === 0 ? (
                <tr>
                  <td className="px-4 py-6 text-muted" colSpan={5}>
                    No active sessions.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-lg border border-border bg-panel p-4">
        <h2 className="text-sm font-semibold text-white">Change password</h2>
        <form onSubmit={submitPassword} className="mt-3 space-y-3">
          <div className="flex flex-wrap gap-3">
            <label className="text-xs text-muted">
              Current password
              <input
                required
                type="password"
                value={current}
                onChange={(event) => setCurrent(event.target.value)}
                className="mt-1 w-56 rounded-md border border-border bg-base px-3 py-2 text-sm text-white"
              />
            </label>
            <label className="text-xs text-muted">
              New password
              <input
                required
                type="password"
                minLength={10}
                value={next}
                onChange={(event) => setNext(event.target.value)}
                className="mt-1 w-56 rounded-md border border-border bg-base px-3 py-2 text-sm text-white"
              />
            </label>
          </div>
          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-accent px-3 py-2 text-xs font-medium text-white hover:opacity-90 disabled:opacity-60"
          >
            {busy ? "Updating…" : "Change password"}
          </button>
        </form>
      </section>

      {message ? <p className="text-xs text-emerald-300">{message}</p> : null}
      {error ? <p className="text-xs text-red-300">{error}</p> : null}
    </div>
  );
}
