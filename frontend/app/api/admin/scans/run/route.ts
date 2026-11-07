import { NextResponse } from "next/server";

import { API_BASE_URL } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function POST() {
  const adminKey = process.env.ADMIN_API_KEY;
  if (!adminKey) {
    return NextResponse.json(
      { error: "ADMIN_API_KEY is not configured for the web app." },
      { status: 503 },
    );
  }

  try {
    const response = await fetch(`${API_BASE_URL}/admin/scans/run`, {
      method: "POST",
      cache: "no-store",
      headers: { "X-Admin-Key": adminKey },
    });
    const body = (await response.json()) as unknown;
    return NextResponse.json(body, { status: response.status });
  } catch {
    return NextResponse.json(
      { error: "The FastAPI backend is unreachable." },
      { status: 502 },
    );
  }
}
