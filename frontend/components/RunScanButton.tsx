"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function RunScanButton() {
  const router = useRouter();
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setRunning(true);
    setMessage(null);
    setError(null);
    try {
      const response = await fetch("/api/admin/scans/run", { method: "POST" });
      const body = (await response.json()) as {
        id?: number;
        matches_count?: number;
        status?: string;
        detail?: string;
        error?: string;
      };
      if (!response.ok) {
        throw new Error(
          (typeof body.detail === "string" ? body.detail : body.error) ??
            "Scan failed.",
        );
      }
      setMessage(
        `Scan #${body.id ?? "?"} ${body.status ?? "completed"} · ${
          body.matches_count ?? 0
        } matches`,
      );
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unexpected error.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={() => void run()}
        disabled={running}
        className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-60"
      >
        {running ? "Scanning stored candles…" : "Run scan now"}
      </button>
      {message ? <p className="text-xs text-emerald-300">{message}</p> : null}
      {error ? <p className="text-xs text-red-300">{error}</p> : null}
    </div>
  );
}
