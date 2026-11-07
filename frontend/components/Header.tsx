import Link from "next/link";

import { HealthIndicator } from "@/components/HealthIndicator";
import { LogoutButton } from "@/components/LogoutButton";
import { fetchCurrentUser } from "@/lib/serverAuth";

export async function Header({
  title,
  subtitle,
}: {
  title: string;
  subtitle?: string;
}) {
  const user = await fetchCurrentUser();

  return (
    <header className="flex flex-col gap-3 border-b border-border bg-panel/60 px-6 py-4 md:flex-row md:items-center md:justify-between">
      <div>
        <h1 className="text-lg font-semibold text-white">{title}</h1>
        {subtitle ? <p className="text-xs text-muted">{subtitle}</p> : null}
      </div>
      <div className="flex items-center gap-4">
        <HealthIndicator />
        {user ? (
          <>
            <Link
              href="/dashboard/profile"
              className="text-xs text-muted hover:text-white"
            >
              {user.full_name}
            </Link>
            <LogoutButton />
          </>
        ) : (
          <Link
            href="/login"
            className="rounded-md border border-border px-3 py-1.5 text-xs text-muted transition hover:text-white"
          >
            Sign in
          </Link>
        )}
      </div>
    </header>
  );
}
