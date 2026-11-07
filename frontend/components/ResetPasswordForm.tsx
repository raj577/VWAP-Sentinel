"use client";

import Link from "next/link";
import { useState } from "react";

import { PasswordInput } from "@/components/auth/PasswordInput";
import { buttonClasses } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { AuthApiError, resetPassword } from "@/services/auth";

export function ResetPasswordForm({ initialToken }: { initialToken: string }) {
  const [token, setToken] = useState(initialToken);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setFormError(null);
    const next: Record<string, string> = {};
    if (!token.trim()) next.token = "Reset token is required.";
    if (password.length < 10) next.password = "Use at least 10 characters.";
    if (confirm !== password) next.confirm = "Passwords do not match.";
    setErrors(next);
    if (Object.keys(next).length) return;

    setBusy(true);
    try {
      const response = await resetPassword({
        token: token.trim(),
        new_password: password,
      });
      setMessage(response.message);
    } catch (caught) {
      setFormError(
        caught instanceof AuthApiError ? caught.message : "Reset failed.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (message) {
    return (
      <div className="space-y-4 text-sm">
        <p className="rounded-xl border border-mint/25 bg-mint/10 p-3 text-mint">
          {message}
        </p>
        <Link
          href="/login"
          className={buttonClasses({ size: "md", className: "w-full" })}
        >
          Sign in
        </Link>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      <Input
        label="Reset token"
        name="token"
        value={token}
        onChange={(event) => setToken(event.target.value)}
        error={errors.token}
        disabled={busy}
      />
      <PasswordInput
        id="reset-password"
        label="New password"
        name="new_password"
        autoComplete="new-password"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        error={errors.password}
        hint="10+ characters with at least three of: lowercase, uppercase, digit, symbol."
        disabled={busy}
      />
      <PasswordInput
        id="reset-confirm"
        label="Confirm new password"
        name="confirm"
        autoComplete="new-password"
        value={confirm}
        onChange={(event) => setConfirm(event.target.value)}
        error={errors.confirm}
        disabled={busy}
      />
      {formError ? (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2.5 text-xs text-red-200" role="alert">
          {formError}
        </div>
      ) : null}
      <button
        type="submit"
        disabled={busy}
        className={buttonClasses({ size: "md", className: "w-full" })}
      >
        {busy ? "Updating…" : "Set new password"}
      </button>
    </form>
  );
}
