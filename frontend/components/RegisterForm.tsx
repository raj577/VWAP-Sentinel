"use client";

import Link from "next/link";
import { useState } from "react";

import { PasswordInput } from "@/components/auth/PasswordInput";
import { buttonClasses } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { AuthApiError, register } from "@/services/auth";
import type { AuthMessage } from "@/types/auth";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function RegisterForm() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<AuthMessage | null>(null);

  function validate(): boolean {
    const next: Record<string, string> = {};
    if (fullName.trim().length < 2) next.fullName = "Enter your full name.";
    if (!email.trim()) next.email = "Email address is required.";
    else if (!EMAIL_PATTERN.test(email.trim())) next.email = "Enter a valid email address.";
    if (password.length < 10) next.password = "Use at least 10 characters.";
    if (confirm !== password) next.confirm = "Passwords do not match.";
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setFormError(null);
    if (!validate()) return;
    setBusy(true);
    try {
      setResult(
        await register({
          full_name: fullName.trim(),
          email: email.trim(),
          password,
        }),
      );
    } catch (caught) {
      if (caught instanceof AuthApiError) {
        setFormError(
          caught.status === 409
            ? "Unable to register with this email. Try signing in instead."
            : caught.status === 429
              ? "Too many attempts. Please wait a minute and try again."
              : caught.message,
        );
      } else {
        setFormError("Registration failed. Please try again.");
      }
    } finally {
      setBusy(false);
    }
  }

  if (result) {
    return (
      <div className="space-y-4 text-sm">
        <p className="rounded-xl border border-mint/25 bg-mint/10 p-3 text-mint">
          {result.message}
        </p>
        {result.dev_token ? (
          <p className="rounded-xl border border-amber-400/25 bg-amber-400/10 p-3 text-xs leading-relaxed text-amber-200">
            Development mode:{" "}
            <Link
              href={`/verify-email?token=${encodeURIComponent(result.dev_token)}`}
              className="underline"
            >
              verify this account now
            </Link>
            . Disable `AUTH_DEV_EXPOSE_TOKENS` outside development.
          </p>
        ) : null}
        <Link
          href="/login"
          className={buttonClasses({ variant: "secondary", className: "w-full" })}
        >
          Go to sign in
        </Link>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      <Input
        label="Full name"
        name="full_name"
        autoComplete="name"
        value={fullName}
        onChange={(event) => setFullName(event.target.value)}
        error={errors.fullName}
        disabled={busy}
      />
      <Input
        label="Email address"
        name="email"
        type="email"
        autoComplete="email"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        error={errors.email}
        disabled={busy}
      />
      <PasswordInput
        id="register-password"
        label="Password"
        name="password"
        autoComplete="new-password"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        error={errors.password}
        hint="10+ characters with at least three of: lowercase, uppercase, digit, symbol."
        disabled={busy}
      />
      <PasswordInput
        id="register-confirm"
        label="Confirm password"
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
        {busy ? "Creating account…" : "Create account"}
      </button>
      <p className="text-center text-[11px] text-mist/70">
        Already registered?{" "}
        <Link href="/login" className="text-mint/90 hover:text-mint">
          Sign in
        </Link>
      </p>
    </form>
  );
}
