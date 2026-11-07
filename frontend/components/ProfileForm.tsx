"use client";

import { useState } from "react";

import { AuthApiError, updateProfile } from "@/services/auth";

export function ProfileForm({ initialName }: { initialName: string }) {
  const [fullName, setFullName] = useState(initialName);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await updateProfile(fullName);
      setMessage("Profile updated.");
    } catch (caught) {
      setError(
        caught instanceof AuthApiError ? caught.message : "Update failed.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <label className="block text-xs text-muted">
        Full name
        <input
          required
          value={fullName}
          onChange={(event) => setFullName(event.target.value)}
          className="mt-1 w-full max-w-md rounded-md border border-border bg-base px-3 py-2 text-sm text-white"
        />
      </label>
      {message ? <p className="text-xs text-emerald-300">{message}</p> : null}
      {error ? <p className="text-xs text-red-300">{error}</p> : null}
      <button
        type="submit"
        disabled={busy}
        className="rounded-md bg-accent px-3 py-2 text-xs font-medium text-white hover:opacity-90 disabled:opacity-60"
      >
        {busy ? "Saving…" : "Save profile"}
      </button>
    </form>
  );
}
