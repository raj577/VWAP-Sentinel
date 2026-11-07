import { Sidebar } from "@/components/Sidebar";
import { requireUser } from "@/lib/serverAuth";

export default async function AppLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const user = await requireUser();
  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <Sidebar roles={user.roles} />
      <div className="flex min-w-0 flex-1 flex-col">{children}</div>
    </div>
  );
}
