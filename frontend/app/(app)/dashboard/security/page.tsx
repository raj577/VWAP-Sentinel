export const dynamic = "force-dynamic";

import { Header } from "@/components/Header";
import { SessionsPanel } from "@/components/SessionsPanel";
import { requireUser } from "@/lib/serverAuth";

export default async function SecurityPage() {
  await requireUser();
  return (
    <>
      <Header title="Security" subtitle="Password, sessions and device management" />
      <main className="flex-1 p-4 sm:p-6 lg:p-8">
        <SessionsPanel />
      </main>
    </>
  );
}
