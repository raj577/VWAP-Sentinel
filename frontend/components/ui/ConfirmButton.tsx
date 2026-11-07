"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function ConfirmButton({
  label,
  confirmTitle,
  confirmMessage,
  path,
  method = "POST",
  body,
  confirmLabel = "Confirm",
  danger = false,
  onDone,
}: {
  label: string;
  confirmTitle: string;
  confirmMessage: string;
  path: string;
  method?: "POST" | "PATCH" | "DELETE";
  body?: unknown;
  confirmLabel?: string;
  danger?: boolean;
  onDone?: () => void;
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function confirm() {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`/api/admin${path}`, {
        method,
        headers: body
          ? { "Content-Type": "application/json" }
          : undefined,
        body: body ? JSON.stringify(body) : undefined,
        cache: "no-store",
      });
      if (!response.ok) {
        let detail = `Request failed (${response.status})`;
        try {
          const payload = (await response.json()) as { detail?: unknown };
          if (typeof payload.detail === "string") detail = payload.detail;
        } catch {
          // keep fallback
        }
        setError(detail);
        return;
      }
      setOpen(false);
      onDone?.();
      router.refresh();
    } catch {
      setError("The backend is unreachable.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={`text-xs hover:underline ${danger ? "text-red-300" : "text-mint"}`}
      >
        {label}
      </button>
      {open ? (
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="confirm-title"
        >
          <div className="w-full max-w-sm rounded-2xl border border-white/10 bg-card p-5 shadow-2xl">
            <h2 id="confirm-title" className="text-sm font-semibold text-[#F5F7FA]">
              {confirmTitle}
            </h2>
            <p className="mt-2 text-xs leading-relaxed text-mist">{confirmMessage}</p>
            {error ? <p className="mt-2 text-xs text-red-300">{error}</p> : null}
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setOpen(false)}
                disabled={busy}
                className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-mist hover:bg-white/5"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => void confirm()}
                disabled={busy}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium disabled:opacity-60 ${
                  danger
                    ? "bg-red-500/90 text-white hover:bg-red-500"
                    : "bg-mint text-[#04120b] hover:bg-[#3bf19c]"
                }`}
              >
                {busy ? "Working…" : confirmLabel}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
