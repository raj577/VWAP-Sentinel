"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AuthApiError, resendVerification, verifyEmail } from "@/services/auth";

export function VerifyEmailPanel({ initialToken }: { initialToken: string }) {
  const [token, setToken] = useState(initialToken);
  const [state, setState] = useState<"idle" | "working" | "ok" | "error">(
    initialToken ? "working" : "idle",
  );
  const [message, setMessage] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [resendMessage, setResendMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!initialToken) return;
    let cancelled = false;
    async function run() {
      try {
        const response = await verifyEmail(initialToken);
        if (!cancelled) {
          setState("ok");
          setMessage(response.message);
        }
      } catch (caught) {
        if (!cancelled) {
          setState("error");
          setMessage(
            caught instanceof AuthApiError
              ? caught.message
              : "Verification failed.",
          );
        }
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, [initialToken]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setState("working");
    try {
      const response = await verifyEmail(token);
      setState("ok");
      setMessage(response.message);
    } catch (caught) {
      setState("error");
      setMessage(
        caught instanceof AuthApiError ? caught.message : "Verification failed.",
      );
    }
  }

  async function resend(event: React.FormEvent) {
    event.preventDefault();
    setResendMessage(null);
    try {
      const response = await resendVerification(email);
      setResendMessage(response.message);
    } catch (caught) {
      setResendMessage(
        caught instanceof AuthApiError ? caught.message : "Could not resend.",
      );
    }
  }

  return (
    <div className="space-y-4 text-sm">
      {state === "working" ? <p className="text-muted">Verifying…</p> : null}
      {message ? (
        <p
          className={`rounded-md border p-3 ${
            state === "ok"
              ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-200"
              : "border-red-500/40 bg-red-500/10 text-red-200"
          }`}
        >
          {message}
        </p>
      ) : null}

      {state === "idle" || state === "error" ? (
        <form onSubmit={submit} className="space-y-3">
          <label className="block text-xs text-muted">
            Verification token
            <input
              required
              value={token}
              onChange={(event) => setToken(event.target.value)}
              className="mt-1 w-full rounded-md border border-border bg-base px-3 py-2 text-sm text-white"
            />
          </label>
          <button
            type="submit"
            className="rounded-md bg-accent px-3 py-2 text-xs font-medium text-white hover:opacity-90"
          >
            Verify email
          </button>
        </form>
      ) : null}

      {state === "ok" ? (
        <Link href="/login" className="text-accent hover:underline">
          Continue to sign in
        </Link>
      ) : null}

      <form onSubmit={resend} className="space-y-2 border-t border-border pt-4">
        <p className="text-xs text-muted">Need a new verification email?</p>
        <input
          required
          type="email"
          placeholder="your email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          className="w-full rounded-md border border-border bg-base px-3 py-2 text-sm text-white"
        />
        <button
          type="submit"
          className="rounded-md border border-border px-3 py-2 text-xs text-white hover:bg-white/5"
        >
          Resend verification
        </button>
        {resendMessage ? (
          <p className="text-xs text-muted">{resendMessage}</p>
        ) : null}
      </form>
    </div>
  );
}
