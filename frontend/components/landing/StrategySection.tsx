import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Check, ShieldIcon } from "@/components/ui/icons";

const POINTS = [
  "Observe price relative to contract-start AVWAP.",
  "Identify small candles near the AVWAP anchor.",
  "Detect repeated interactions with the anchor.",
  "Distinguish touches, hugging and consolidation.",
  "Review the setup with session VWAP as additional context.",
];

export function StrategySection() {
  return (
    <section id="strategies" className="relative scroll-mt-24 border-y border-white/[0.06] bg-ink2/50 py-20 sm:py-24">
      <div className="mx-auto grid w-full max-w-7xl gap-10 px-4 sm:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:px-8">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky">
            Methodology
          </p>
          <h2 className="mt-3 text-3xl font-semibold tracking-[-0.02em] text-[#F5F7FA] sm:text-4xl">
            Designed Around Price and Volume.
          </h2>
          <p className="mt-4 max-w-xl text-[15px] leading-relaxed text-mist">
            AVWAP Scanner does not attempt to predict direction. It structures
            the observation: where price sits relative to the contract anchor,
            how candles behave near it, and whether the interaction repeats.
          </p>

          <ul className="mt-7 space-y-3">
            {POINTS.map((point) => (
              <li key={point} className="flex items-start gap-3 text-sm text-[#DCE4EE]">
                <span className="mt-0.5 flex h-5 w-5 flex-none items-center justify-center rounded-full border border-mint/25 bg-mint/10 text-mint">
                  <Check size={12} />
                </span>
                {point}
              </li>
            ))}
          </ul>

          <p className="mt-7 max-w-xl text-xs leading-relaxed text-mist/80">
            The scanner is a technical heuristic, not a recommendation engine.
            It does not guarantee profitable trades or predict market
            direction.
          </p>
        </div>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[#F5F7FA]">
              What the scanner evaluates
            </h3>
            <Badge tone="mint">Configurable</Badge>
          </div>

          <div className="mt-5 space-y-4">
            {[
              { label: "Contract AVWAP", value: "Anchor: first contract candle", tone: "text-[#F0616D]" },
              { label: "Session VWAP", value: "Resets each trading day", tone: "text-sky" },
              { label: "Candle body ratio", value: "Small-body threshold", tone: "text-mint" },
              { label: "Candle range", value: "ATR-scaled range cap", tone: "text-mint" },
              { label: "Pattern window", value: "1–5 completed 1-hour candles", tone: "text-[#F5F7FA]" },
            ].map((item) => (
              <div key={item.label} className="flex items-center justify-between gap-4 border-b border-white/[0.06] pb-3 last:border-0 last:pb-0">
                <div>
                  <p className="text-[13px] text-[#DCE4EE]">{item.label}</p>
                  <p className="text-[11px] text-mist">{item.value}</p>
                </div>
                <span className={`font-mono text-xs ${item.tone}`}>●</span>
              </div>
            ))}
          </div>

          <div className="mt-6 flex items-start gap-2.5 rounded-xl border border-white/[0.08] bg-ink/50 p-3">
            <ShieldIcon size={16} className="mt-0.5 flex-none text-mist" />
            <p className="text-[11px] leading-relaxed text-mist">
              Completed candles only. Forming bars are excluded so historical
              snapshots remain stable.
            </p>
          </div>
        </Card>
      </div>
    </section>
  );
}
