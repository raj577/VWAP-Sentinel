import { getCsrfToken } from "@/lib/csrf";
import type {
  AuthMessage,
  AuthUser,
  SessionList,
  TokenResponse,
} from "@/types/auth";

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
}

export class AuthApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "AuthApiError";
  }
}

async function authRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const method = options.method ?? "GET";
  const headers: Record<string, string> = { Accept: "application/json" };
  if (method !== "GET") {
    headers["Content-Type"] = "application/json";
    const csrf = getCsrfToken();
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }

  const response = await fetch(`/api/auth${path}`, {
    method,
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    cache: "no-store",
  });

  const text = await response.text();
  const payload = text ? (JSON.parse(text) as unknown) : null;
  if (!response.ok) {
    const detail =
      payload && typeof payload === "object" && "detail" in payload
        ? (payload as { detail: unknown }).detail
        : null;
    throw new AuthApiError(
      response.status,
      typeof detail === "string" ? detail : "Request failed.",
    );
  }
  return payload as T;
}

export function register(input: {
  full_name: string;
  email: string;
  password: string;
}): Promise<AuthMessage> {
  return authRequest<AuthMessage>("/register", { method: "POST", body: input });
}

export function login(input: {
  email: string;
  password: string;
}): Promise<TokenResponse> {
  return authRequest<TokenResponse>("/login", { method: "POST", body: input });
}

export function verifyEmail(token: string): Promise<AuthMessage> {
  return authRequest<AuthMessage>("/verify-email", {
    method: "POST",
    body: { token },
  });
}

export function resendVerification(email: string): Promise<AuthMessage> {
  return authRequest<AuthMessage>("/resend-verification", {
    method: "POST",
    body: { email },
  });
}

export function forgotPassword(email: string): Promise<AuthMessage> {
  return authRequest<AuthMessage>("/forgot-password", {
    method: "POST",
    body: { email },
  });
}

export function resetPassword(input: {
  token: string;
  new_password: string;
}): Promise<AuthMessage> {
  return authRequest<AuthMessage>("/reset-password", {
    method: "POST",
    body: input,
  });
}

export function logout(): Promise<AuthMessage> {
  return authRequest<AuthMessage>("/logout", { method: "POST", body: {} });
}

export function logoutAll(): Promise<AuthMessage> {
  return authRequest<AuthMessage>("/logout-all", {
    method: "POST",
    body: {},
  });
}

export function changePassword(input: {
  current_password: string;
  new_password: string;
}): Promise<AuthMessage> {
  return authRequest<AuthMessage>("/change-password", {
    method: "POST",
    body: input,
  });
}

export function fetchMe(): Promise<AuthUser> {
  return authRequest<AuthUser>("/me");
}

export function updateProfile(full_name: string): Promise<AuthUser> {
  return authRequest<AuthUser>("/me", { method: "PATCH", body: { full_name } });
}

export function fetchSessions(): Promise<SessionList> {
  return authRequest<SessionList>("/sessions");
}

export function revokeSession(sessionId: string): Promise<AuthMessage> {
  return authRequest<AuthMessage>(`/sessions/${sessionId}`, {
    method: "DELETE",
  });
}
