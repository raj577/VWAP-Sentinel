"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import type { SchedulerSettings } from "@/types/api";

interface ActionResult {
  ok: boolean;
  detail?: string;
}

async function callAdmin(
  path: string,
  method: "POST" | "PATCH",
  body?: unknown,
): Promise<ActionResult> {
  const response = await fetch(`/api/admin${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (response.ok) return { ok: true };
  let detail = `Request failed (${response.status})`;
  try {
    const payload = (await response.json()) as { detail?: unknown; error?: string };
    detail =
      typeof payload.detail === "string"
        ? payload.detail
        : payload.error ?? detail;
  } catch {
    // keep fallback
  }
  return { ok: false, detail };
}

export function SchedulerControls({ settings }: { settings: SchedulerSettings }) {
  const router = useRouter();
  const [interval, setIntervalValue] = useState(settings.scan_interval_minutes);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(label: string, action: () => Promise<ActionResult>) {
    setBusy(label);
    setError(null);
    setMessage(null);
    try {
      const result = await action();
      if (!result.ok) {
        setError(result.detail ?? "Request failed.");
        return false;
      }
      setMessage(`${label} accepted.`);
      router.refresh();
      return true;
    } catch {
      setError("The backend is unreachable.");
      return false;
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="rounded-lg border border-border bg-panel p-4">
      <h2 className="text-sm font-semibold text-white">Scheduler controls</h2>
      <p className="mt-1 text-xs text-muted">
        Automatic runs happen only while the market is open and the scheduler is
        enabled. Manual actions are still allowed while paused.
      </p>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        {settings.scheduler_enabled ? (
          <button
            type="button"
            disabled={busy !== null}
            onClick={() => {
              if (window.confirm("Pause automatic scheduling?")) {
                void run("Pause", () =>
                  callAdmin("/scheduler/pause", "POST"),
                );
              }
            }}
            className="rounded-md border border-amber-500/50 px-3 py-2 text-xs text-amber-200 hover:bg-amber-500/10 disabled:opacity-60"
          >
            Pause scheduler
          </button>
        ) : (
          <button
            type="button"
            disabled={busy !== null}
            onClick={() =>
              void run("Resume", () => callAdmin("/scheduler/resume", "POST"))
            }
            className="rounded-md border border-emerald-500/50 px-3 py-2 text-xs text-emerald-200 hover:bg-emerald-500/10 disabled:opacity-60"
          >
            Resume scheduler
          </button>
        )}

        <button
          type="button"
          disabled={busy !== null}
          onClick={() => {
            if (
              window.confirm(
                "Queue ingestion followed by a scan? This may take several minutes.",
              )
            ) {
              void run("Market data refresh", () =>
                callAdmin("/pipeline/refresh", "POST"),
              );
            }
          }}
          className="rounded-md bg-accent px-3 py-2 text-xs font-medium text-white hover:opacity-90 disabled:opacity-60"
        >
          Update market data now
        </button>

        <button
          type="button"
          disabled={busy !== null}
          onClick={() => {
            if (!window.confirm("Run the scanner on stored candles?")) return;
            void (async () => {
              const result = await callAdmin("/pipeline/run-scanner", "POST", {});
              if (
                !result.ok &&
                (result.detail ?? "").toLowerCase().includes("stale")
              ) {
                if (
                  window.confirm(
                    `${result.detail}\n\nScan with stale data anyway?`,
                  )
                ) {
                  await run("Scan with stale data", () =>
                    callAdmin("/pipeline/run-scanner", "POST", {
                      confirm_stale: true,
                    }),
                  );
                }
                return;
              }
              if (!result.ok) {
                setError(result.detail ?? "Scan request failed.");
                return;
              }
              setMessage("Scanner job accepted.");
              router.refresh();
            })();
          }}
          className="rounded-md border border-border px-3 py-2 text-xs text-white hover:bg-white/5 disabled:opacity-60"
        >
          Run scanner now
        </button>
      </div>

      <div className="mt-4 flex flex-wrap items-end gap-2 text-xs text-muted">
        <label className="flex flex-col gap-1">
          Refresh interval (minutes)
          <input
            type="number"
            min={1}
            max={1440}
            value={interval}
            onChange={(event) => setIntervalValue(Number(event.target.value))}
            className="w-32 rounded-md border border-border bg-base px-2 py-1.5 text-xs text-white"
          />
        </label>
        <button
          type="button"
          disabled={busy !== null || interval < 1 || interval > 1440}
          onClick={() =>
            void run("Interval update", () =>
              callAdmin("/scheduler/settings", "PATCH", {
                scan_interval_minutes: interval,
              }),
            )
          }
          className="rounded-md border border-border px-3 py-2 text-xs text-white hover:bg-white/5 disabled:opacity-60"
        >
          Save interval
        </button>
      </div>

      {message ? (
        <p className="mt-3 text-xs text-emerald-300">{message}</p>
      ) : null}
      {error ? <p className="mt-3 text-xs text-red-300">{error}</p> : null}
      {busy ? <p className="mt-2 text-xs text-muted">Working: {busy}…</p> : null}
    </section>
  );
}
