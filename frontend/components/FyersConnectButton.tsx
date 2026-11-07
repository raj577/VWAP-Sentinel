"use client";

import { useState } from "react";

export function FyersConnectButton() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function connect() {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/fyers/login-url", {
        cache: "no-store",
      });
      const body = (await response.json()) as {
        login_url?: string;
        detail?: string;
        error?: string;
      };
      if (!response.ok || !body.login_url) {
        throw new Error(body.detail ?? body.error ?? "Could not start FYERS login.");
      }
      window.location.href = body.login_url;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unexpected error.");
      setLoading(false);
    }
  }

  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={() => void connect()}
        disabled={loading}
        className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-60"
      >
        {loading ? "Opening FYERS…" : "Connect / Re-login FYERS"}
      </button>
      {error ? <p className="text-xs text-red-300">{error}</p> : null}
    </div>
  );
}
