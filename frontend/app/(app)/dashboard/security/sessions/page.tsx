export const dynamic = "force-dynamic";

import { Header } from "@/components/Header";
import { SessionsPanel } from "@/components/SessionsPanel";
import { requireUser } from "@/lib/serverAuth";

export default async function SecurityPage() {
  await requireUser();

  return (
    <>
      <Header
        title="Security"
        subtitle="Sessions, password and device management"
      />
      <main className="flex-1 space-y-6 p-6">
        <SessionsPanel />
      </main>
    </>
  );
}
