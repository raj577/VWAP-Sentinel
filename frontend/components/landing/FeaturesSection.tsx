import { Card } from "@/components/ui/Card";
import { AnchorIcon, HistoryIcon, RadarIcon, TargetIcon } from "@/components/ui/icons";

const FEATURES = [
  {
    icon: AnchorIcon,
    title: "Contract-Anchored AVWAP",
    body: "Track VWAP from the beginning of the futures contract rather than resetting it every trading session.",
    accent: "text-mint bg-mint/10 border-mint/20",
  },
  {
    icon: TargetIcon,
    title: "Precision Consolidation Detection",
    body: "Identify small candles touching or hugging contract AVWAP using configurable body and range thresholds.",
    accent: "text-sky bg-sky/10 border-sky/20",
  },
  {
    icon: RadarIcon,
    title: "Automated Futures Scanning",
    body: "Scan multiple active NSE stock futures from one centralized engine, with every expiry kept isolated.",
    accent: "text-mint bg-mint/10 border-mint/20",
  },
  {
    icon: HistoryIcon,
    title: "Historical Scan Intelligence",
    body: "Review immutable scan snapshots and understand how potential setups evolve between runs.",
    accent: "text-sky bg-sky/10 border-sky/20",
  },
];

export function FeaturesSection() {
  return (
    <section id="features" className="relative scroll-mt-24 py-20 sm:py-24">
      <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-mint">
            Product
          </p>
          <h2 className="mt-3 text-3xl font-semibold tracking-[-0.02em] text-[#F5F7FA] sm:text-4xl">
            Market Structure, Without the Noise.
          </h2>
          <p className="mt-4 text-[15px] leading-relaxed text-mist">
            Everything is built around one repeatable question: how is price
            behaving relative to the contract&apos;s anchored VWAP?
          </p>
        </div>

        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((feature) => {
            const Icon = feature.icon;
            return (
              <Card
                key={feature.title}
                className="group p-5 transition-all duration-300 hover:-translate-y-1 hover:border-white/[0.16]"
              >
                <span
                  className={`inline-flex h-11 w-11 items-center justify-center rounded-xl border ${feature.accent}`}
                >
                  <Icon size={21} />
                </span>
                <h3 className="mt-4 text-[15px] font-semibold text-[#F5F7FA]">
                  {feature.title}
                </h3>
                <p className="mt-2 text-[13px] leading-relaxed text-mist">
                  {feature.body}
                </p>
              </Card>
            );
          })}
        </div>
      </div>
    </section>
  );
}
