"use client";

import Link from "next/link";
import { useState } from "react";

import { buttonClasses } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { AuthApiError, forgotPassword } from "@/services/auth";
import type { AuthMessage } from "@/types/auth";

export function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<AuthMessage | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    if (!email.trim()) {
      setError("Email address is required.");
      return;
    }
    setBusy(true);
    try {
      setResult(await forgotPassword(email.trim()));
    } catch (caught) {
      setError(
        caught instanceof AuthApiError
          ? caught.message
          : "Request failed. Please try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (result) {
    return (
      <div className="space-y-4 text-sm">
        <p className="rounded-xl border border-white/10 bg-white/[0.03] p-3 text-mist">
          {result.message}
        </p>
        {result.dev_token ? (
          <Link
            href={`/reset-password?token=${encodeURIComponent(result.dev_token)}`}
            className="block text-xs text-amber-300 underline"
          >
            Development mode: open reset link
          </Link>
        ) : null}
        <Link
          href="/login"
          className={buttonClasses({ variant: "secondary", className: "w-full" })}
        >
          Back to sign in
        </Link>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <Input
        label="Email address"
        name="email"
        type="email"
        autoComplete="email"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        error={error ?? undefined}
        disabled={busy}
      />
      <button
        type="submit"
        disabled={busy}
        className={buttonClasses({ size: "md", className: "w-full" })}
      >
        {busy ? "Sending…" : "Send reset link"}
      </button>
      <p className="text-center text-[11px] text-mist/70">
        For security, the response is the same whether or not the account exists.
      </p>
    </form>
  );
}
