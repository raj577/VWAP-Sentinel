import { Header } from "@/components/Header";

export default function SubscriptionPage() {
  return (
    <>
      <Header
        title="Subscription"
        subtitle="Trials and plans arrive in Phase 6"
      />
      <main className="flex-1 p-6">
        <div className="rounded-lg border border-border bg-panel p-6 text-sm text-muted">
          The entitlement engine will expose plan features, trial status and
          usage limits from the backend. No billing logic is implemented yet.
        </div>
      </main>
    </>
  );
}
