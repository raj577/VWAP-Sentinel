"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { PasswordInput } from "@/components/auth/PasswordInput";
import { buttonClasses } from "@/components/ui/Button";
import { Mail } from "@/components/ui/icons";
import { Input } from "@/components/ui/Input";
import { AuthApiError, login } from "@/services/auth";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [emailError, setEmailError] = useState<string | undefined>();
  const [passwordError, setPasswordError] = useState<string | undefined>();
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function validate(): boolean {
    let ok = true;
    if (!email.trim()) {
      setEmailError("Email address is required.");
      ok = false;
    } else if (!EMAIL_PATTERN.test(email.trim())) {
      setEmailError("Enter a valid email address.");
      ok = false;
    } else {
      setEmailError(undefined);
    }

    if (!password) {
      setPasswordError("Password is required.");
      ok = false;
    } else {
      setPasswordError(undefined);
    }
    return ok;
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setFormError(null);
    if (!validate()) return;

    setBusy(true);
    try {
      const response = await login({ email: email.trim(), password });
      const admin = response.user.roles.some(
        (role) => role === "ADMIN" || role === "SUPER_ADMIN",
      );
      router.push(admin ? "/admin" : "/dashboard");
      router.refresh();
    } catch (caught) {
      if (caught instanceof AuthApiError) {
        setFormError(
          caught.status === 429
            ? "Too many attempts. Please wait a minute and try again."
            : caught.message,
        );
      } else {
        setFormError("Unable to sign in right now. Please try again.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      <Input
        label="Email address"
        name="email"
        type="email"
        autoComplete="email"
        placeholder="you@example.com"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        error={emailError}
        icon={<Mail size={16} />}
        disabled={busy}
      />

      <PasswordInput
        id="login-password"
        name="password"
        autoComplete="current-password"
        placeholder="Enter your password"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        error={passwordError}
        disabled={busy}
      />

      {formError ? (
        <div
          role="alert"
          aria-live="polite"
          className="rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2.5 text-xs text-red-200"
        >
          {formError}
        </div>
      ) : null}

      <div className="flex items-center justify-between text-xs">
        <Link
          href="/forgot-password"
          className="text-mist transition-colors hover:text-[#F5F7FA]"
        >
          Forgot password?
        </Link>
        <Link
          href="/register"
          className="text-mint/90 transition-colors hover:text-mint"
        >
          Create account
        </Link>
      </div>

      <button
        type="submit"
        disabled={busy}
        className={buttonClasses({ size: "md", className: "w-full" })}
      >
        {busy ? (
          <>
            <span
              aria-hidden
              className="h-4 w-4 animate-spin rounded-full border-2 border-[#04120b]/30 border-t-[#04120b]"
            />
            Signing in…
          </>
        ) : (
          "Sign In"
        )}
      </button>

      <p className="pt-1 text-center text-[11px] leading-relaxed text-mist/70">
        Access is limited to registered accounts. Email verification is
        required before the first sign-in.
      </p>
    </form>
  );
}
