"use client";

import { useEffect, useState } from "react";

import { API_BASE_URL } from "@/lib/api";

type State = "checking" | "online" | "offline";

export function HealthIndicator() {
  const [state, setState] = useState<State>("checking");

  useEffect(() => {
    let cancelled = false;

    async function probe() {
      try {
        const response = await fetch(`${API_BASE_URL}/health/live`, {
          cache: "no-store",
        });
        if (!cancelled) setState(response.ok ? "online" : "offline");
      } catch {
        if (!cancelled) setState("offline");
      }
    }

    void probe();
    const timer = setInterval(() => void probe(), 30_000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  const dot =
    state === "online"
      ? "bg-emerald-400"
      : state === "offline"
        ? "bg-red-500"
        : "bg-amber-400";

  return (
    <span className="flex items-center gap-2 text-xs text-muted">
      <span className={`h-2 w-2 rounded-full ${dot}`} />
      API {state}
    </span>
  );
}
