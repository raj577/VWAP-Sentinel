import { NextRequest, NextResponse } from "next/server";

import { API_BASE_URL } from "@/lib/api";

export const dynamic = "force-dynamic";

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const search = new URL(request.url).search;
  const target = `${API_BASE_URL}/auth/${path.join("/")}${search}`;

  const headers: Record<string, string> = { Accept: "application/json" };
  const cookie = request.headers.get("cookie");
  if (cookie) headers["cookie"] = cookie;
  const csrf = request.headers.get("x-csrf-token");
  if (csrf) headers["x-csrf-token"] = csrf;

  const init: RequestInit = {
    method: request.method,
    headers,
    cache: "no-store",
  };
  if (request.method !== "GET" && request.method !== "HEAD") {
    headers["Content-Type"] = "application/json";
    init.body = await request.text();
  }

  try {
    const response = await fetch(target, init);
    const text = await response.text();
    const proxied = new NextResponse(text, {
      status: response.status,
      headers: { "Content-Type": "application/json" },
    });
    for (const value of response.headers.getSetCookie()) {
      proxied.headers.append("set-cookie", value);
    }
    return proxied;
  } catch {
    return NextResponse.json(
      { detail: "The FastAPI backend is unreachable." },
      { status: 502 },
    );
  }
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
