import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { API_BASE_URL } from "@/lib/api";
import type { AuthUser } from "@/types/auth";

export async function cookieHeader(): Promise<string> {
  return (await cookies()).toString();
}

export async function authHeaders(): Promise<Record<string, string>> {
  return { Cookie: await cookieHeader() };
}

export async function fetchCurrentUser(): Promise<AuthUser | null> {
  const cookie = await cookieHeader();
  if (!cookie) return null;
  try {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
      headers: { Cookie: cookie, Accept: "application/json" },
      cache: "no-store",
    });
    if (!response.ok) return null;
    return (await response.json()) as AuthUser;
  } catch {
    return null;
  }
}

export async function requireUser(): Promise<AuthUser> {
  const user = await fetchCurrentUser();
  if (!user) redirect("/login");
  return user;
}

export async function requireAdmin(): Promise<AuthUser> {
  const user = await requireUser();
  if (!user.roles.some((role) => role === "ADMIN" || role === "SUPER_ADMIN")) {
    redirect("/");
  }
  return user;
}

export function isAdmin(user: AuthUser | null): boolean {
  return Boolean(
    user?.roles.some((role) => role === "ADMIN" || role === "SUPER_ADMIN"),
  );
}
