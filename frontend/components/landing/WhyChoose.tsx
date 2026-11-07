import { Card } from "@/components/ui/Card";
import { Check, Close } from "@/components/ui/icons";

const ROWS = [
  "Centralized scanning across active futures",
  "Consistent AVWAP methodology per contract",
  "Immutable historical scan snapshots",
  "Structured futures analysis in one workflow",
  "One dashboard for multiple instruments",
  "Session VWAP alongside the contract anchor",
];

export function WhyChoose() {
  return (
    <section className="relative py-20 sm:py-24">
      <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-mint">
            Why AVWAP Scanner
          </p>
          <h2 className="mt-3 text-3xl font-semibold tracking-[-0.02em] text-[#F5F7FA] sm:text-4xl">
            A Consistent Process, Not a Chart Marathon.
          </h2>
          <p className="mt-4 text-[15px] leading-relaxed text-mist">
            Manual review across dozens of contracts invites inconsistency.
            A structured workflow keeps the criteria identical every session.
          </p>
        </div>

        <div className="mt-10 grid gap-4 md:grid-cols-2">
          <Card className="border-white/[0.06] p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-mist">
              Unstructured review
            </p>
            <ul className="mt-5 space-y-3 text-sm text-mist">
              {[
                "Charts checked ad hoc, in different orders",
                "Criteria drift between sessions",
                "No record of what matched previously",
                "Expiries and symbols mix in memory",
              ].map((item) => (
                <li key={item} className="flex items-start gap-3">
                  <span className="mt-0.5 flex h-5 w-5 flex-none items-center justify-center rounded-full border border-white/10 bg-white/5 text-mist">
                    <Close size={11} />
                  </span>
                  {item}
                </li>
              ))}
            </ul>
          </Card>

          <Card className="border-mint/20 p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-mint">
              AVWAP Scanner workflow
            </p>
            <ul className="mt-5 space-y-3 text-sm text-[#DCE4EE]">
              {ROWS.map((item) => (
                <li key={item} className="flex items-start gap-3">
                  <span className="mt-0.5 flex h-5 w-5 flex-none items-center justify-center rounded-full border border-mint/25 bg-mint/10 text-mint">
                    <Check size={11} />
                  </span>
                  {item}
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    </section>
  );
}
