import { NextRequest, NextResponse } from "next/server";

const API_BASE =
  process.env.API_INTERNAL_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000/api/v1";

const PROTECTED_PREFIXES = [
  "/dashboard",
  "/current",
  "/scans",
  "/chart",
  "/watchlist",
  "/subscription",
  "/admin",
];

function isProtected(pathname: string): boolean {
  return PROTECTED_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

function readCookie(request: NextRequest, name: string): string | null {
  return request.cookies.get(name)?.value ?? null;
}

function clearCookies(response: NextResponse): void {
  for (const name of ["access_token", "refresh_token", "csrf_token"]) {
    response.cookies.set(name, "", { path: "/", maxAge: 0 });
  }
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (!isProtected(pathname)) {
    return NextResponse.next();
  }

  const access = readCookie(request, "access_token");
  if (access) {
    return NextResponse.next();
  }

  const refresh = readCookie(request, "refresh_token");
  if (!refresh) {
    const login = new URL("/login", request.url);
    login.searchParams.set("next", pathname);
    return NextResponse.redirect(login);
  }

  try {
    const response = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Cookie: `refresh_token=${refresh}; csrf_token=${readCookie(request, "csrf_token") ?? ""}`,
        "X-CSRF-Token": readCookie(request, "csrf_token") ?? "",
      },
      body: "{}",
      cache: "no-store",
    });

    if (!response.ok) {
      const login = new URL("/login", request.url);
      const redirect = NextResponse.redirect(login);
      clearCookies(redirect);
      return redirect;
    }

    const redirect = NextResponse.redirect(request.nextUrl.clone());
    for (const cookie of response.headers.getSetCookie()) {
      redirect.headers.append("set-cookie", cookie);
    }
    return redirect;
  } catch {
    const login = new URL("/login", request.url);
    return NextResponse.redirect(login);
  }
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/current",
    "/scans/:path*",
    "/chart/:path*",
    "/watchlist",
    "/subscription",
    "/admin/:path*",
  ],
};
