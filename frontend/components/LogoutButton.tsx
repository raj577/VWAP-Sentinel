"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { logout } from "@/services/auth";

export function LogoutButton() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function signOut() {
    setBusy(true);
    try {
      await logout();
    } catch {
      // Clearing cookies still happens server-side on success; navigate anyway.
    } finally {
      setBusy(false);
      router.push("/login");
      router.refresh();
    }
  }

  return (
    <button
      type="button"
      onClick={() => void signOut()}
      disabled={busy}
      className="rounded-md border border-border px-3 py-1.5 text-xs text-muted transition hover:text-white disabled:opacity-60"
    >
      {busy ? "Signing out…" : "Sign out"}
    </button>
  );
}
