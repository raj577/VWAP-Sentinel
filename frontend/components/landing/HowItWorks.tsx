const STEPS = [
  {
    step: "01",
    title: "Market Data",
    body: "Centralized futures market data is collected through the platform's market-data pipeline and stored in PostgreSQL.",
  },
  {
    step: "02",
    title: "AVWAP Analysis",
    body: "The scanner evaluates contract-start AVWAP, session VWAP and candle structure for every active contract.",
  },
  {
    step: "03",
    title: "Setup Discovery",
    body: "View futures contracts matching the configured consolidation conditions, with immutable scan history.",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="relative scroll-mt-24 border-y border-white/[0.06] bg-ink2/60 py-20 sm:py-24">
      <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky">
            Workflow
          </p>
          <h2 className="mt-3 text-3xl font-semibold tracking-[-0.02em] text-[#F5F7FA] sm:text-4xl">
            From Market Data to Actionable Insights.
          </h2>
        </div>

        <div className="relative mt-12 grid gap-6 md:grid-cols-3">
          <div
            aria-hidden
            className="absolute left-6 right-6 top-7 hidden h-px bg-gradient-to-r from-mint/40 via-sky/40 to-transparent md:block"
          />
          {STEPS.map((step) => (
            <div key={step.step} className="relative rounded-2xl border border-white/[0.08] bg-card/70 p-6">
              <div className="flex h-9 w-9 items-center justify-center rounded-full border border-mint/30 bg-ink font-mono text-xs text-mint">
                {step.step}
              </div>
              <h3 className="mt-4 text-[15px] font-semibold text-[#F5F7FA]">
                {step.title}
              </h3>
              <p className="mt-2 text-[13px] leading-relaxed text-mist">
                {step.body}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
