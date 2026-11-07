import Link from "next/link";

import { LogoutButton } from "@/components/LogoutButton";
import { Sidebar } from "@/components/Sidebar";
import { requireUser } from "@/lib/serverAuth";

export default async function AppLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const user = await requireUser();
  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <Sidebar roles={user.roles} />
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/[0.06] bg-[#0B1220] px-4 py-2 text-xs sm:px-6">
          <p className="text-mist">
            Signed in as <span className="text-[#F5F7FA]">{user.full_name}</span>
            <span className="ml-2 rounded-full border border-white/10 px-2 py-0.5 text-[10px] text-mist">
              {user.roles.join(", ")}
            </span>
          </p>
          <div className="flex items-center gap-3">
            <Link href="/dashboard/profile" className="text-mist hover:text-white">
              Profile
            </Link>
            <Link href="/dashboard/security" className="text-mist hover:text-white">
              Security
            </Link>
            <LogoutButton />
          </div>
        </div>
        <div className="flex min-w-0 flex-1 flex-col">{children}</div>
      </div>
    </div>
  );
}
