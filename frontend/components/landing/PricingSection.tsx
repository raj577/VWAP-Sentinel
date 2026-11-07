import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Check } from "@/components/ui/icons";

const PLANS = [
  {
    name: "Free",
    description: "A focused starting point for exploring the scanner.",
    features: ["Current scan view", "Chart visualisation", "Basic watchlist", "Limited history"],
    cta: "Explore Free Plan",
    featured: false,
  },
  {
    name: "Pro",
    description: "Deeper analysis for active futures research workflows.",
    features: [
      "Full scan history",
      "Advanced filters",
      "Full futures universe",
      "Strategy presets",
      "Historical comparisons",
    ],
    cta: "Choose Pro",
    featured: true,
  },
  {
    name: "Premium",
    description: "Complete access for demanding research routines.",
    features: [
      "Everything in Pro",
      "Premium research guides",
      "Extended history windows",
      "Priority feature access",
    ],
    cta: "Get Premium",
    featured: false,
  },
];

export function PricingSection() {
  return (
    <section id="pricing" className="relative scroll-mt-24 border-y border-white/[0.06] bg-ink2/50 py-20 sm:py-24">
      <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky">
            Plans
          </p>
          <h2 className="mt-3 text-3xl font-semibold tracking-[-0.02em] text-[#F5F7FA] sm:text-4xl">
            Plans That Follow the Research.
          </h2>
          <p className="mt-4 text-[15px] leading-relaxed text-mist">
            Subscription billing is not live yet. Plan capabilities will be
            enforced by the backend entitlement system when plans launch.
          </p>
        </div>

        <div className="mt-10 grid gap-4 lg:grid-cols-3">
          {PLANS.map((plan) => (
            <Card
              key={plan.name}
              className={[
                "relative flex flex-col p-6",
                plan.featured ? "border-mint/30 shadow-[0_30px_80px_-50px_rgba(39,224,138,0.55)]" : "",
              ].join(" ")}
            >
              {plan.featured ? (
                <span className="absolute -top-3 left-6">
                  <Badge tone="mint">Most anticipated</Badge>
                </span>
              ) : null}

              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-[#F5F7FA]">{plan.name}</h3>
                <Badge tone="neutral">Coming soon</Badge>
              </div>
              <p className="mt-2 text-[13px] leading-relaxed text-mist">
                {plan.description}
              </p>

              <div className="mt-5 border-y border-white/[0.06] py-4">
                <p className="text-2xl font-semibold text-[#F5F7FA]">—</p>
                <p className="mt-1 text-[11px] text-mist">
                  Pricing not published
                </p>
              </div>

              <ul className="mt-5 flex-1 space-y-2.5 text-[13px] text-[#DCE4EE]">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2.5">
                    <Check size={14} className="mt-0.5 flex-none text-mint" />
                    {feature}
                  </li>
                ))}
              </ul>

              <Button
                variant={plan.featured ? "primary" : "secondary"}
                className="mt-6 w-full"
                disabled
              >
                {plan.cta} · Coming Soon
              </Button>
            </Card>
          ))}
        </div>

        <p className="mt-6 text-[11px] text-mist/70">
          No payment is collected on this site today. Plan limits will be
          configurable by the platform administrator.
        </p>
      </div>
    </section>
  );
}
