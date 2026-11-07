import { requireAdmin } from "@/lib/serverAuth";

export default async function AdminLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  await requireAdmin();
  return children;
}
