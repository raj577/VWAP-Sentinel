import Link from "next/link";

import { DashboardPreview } from "@/components/landing/DashboardPreview";
import { Button } from "@/components/ui/Button";
import { ArrowRight, Check } from "@/components/ui/icons";

const TRUST_ITEMS = [
  "NSE Stock Futures",
  "Contract-Anchored AVWAP",
  "1-Hour Market Structure",
  "Automated Scanning",
];

export function HeroSection() {
  return (
    <section className="relative overflow-hidden pb-16 pt-28 sm:pb-20 sm:pt-32 lg:pt-36">
      <div aria-hidden className="pointer-events-none absolute inset-0 hero-glow" />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 grid-fade opacity-60"
      />

      <div className="relative mx-auto grid w-full max-w-7xl gap-12 px-4 sm:px-6 lg:grid-cols-[1.02fr_1fr] lg:items-center lg:gap-10 lg:px-8">
        <div className="animate-fade-up">
          <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[11px] font-medium tracking-wide text-mist">
            <span className="h-1.5 w-1.5 rounded-full bg-mint" />
            Precision futures analytics
          </span>

          <h1 className="mt-6 text-balance text-4xl font-semibold leading-[1.08] tracking-[-0.03em] text-[#F5F7FA] sm:text-5xl lg:text-[56px]">
            Find Futures Setups Around{" "}
            <span className="bg-gradient-to-r from-mint via-[#6EE7B7] to-sky bg-clip-text text-transparent">
              Contract-Anchored VWAP.
            </span>
          </h1>

          <p className="mt-6 max-w-xl text-[15px] leading-relaxed text-mist sm:text-base">
            Identify futures contracts consolidating around their
            contract-start AVWAP. Monitor price behaviour, spot potential
            setups and analyse market structure from one powerful scanner.
          </p>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button href="#scanner-preview" size="lg">
              Explore the Scanner <ArrowRight size={17} />
            </Button>
            <Button href="/login" variant="secondary" size="lg">
              Login to Dashboard
            </Button>
          </div>

          <div className="mt-8 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-mist">
            {TRUST_ITEMS.map((item) => (
              <span key={item} className="flex items-center gap-1.5">
                <Check size={14} className="text-mint" />
                {item}
              </span>
            ))}
          </div>

          <p className="mt-6 text-[11px] text-mist/70">
            Illustrative product preview. Not live market data.{" "}
            <Link href="/register" className="text-mint/80 hover:text-mint">
              Create an account
            </Link>{" "}
            to use the scanner.
          </p>
        </div>

        <div className="animate-fade-up [animation-delay:120ms]">
          <div className="animate-soft-float">
            <DashboardPreview />
          </div>
        </div>
      </div>
    </section>
  );
}
