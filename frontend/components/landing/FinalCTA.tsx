import { Button } from "@/components/ui/Button";

export function FinalCTA() {
  return (
    <section className="relative overflow-hidden py-20 sm:py-24">
      <div aria-hidden className="pointer-events-none absolute inset-0 hero-glow opacity-80" />
      <div className="relative mx-auto w-full max-w-4xl px-4 text-center sm:px-6 lg:px-8">
        <h2 className="text-balance text-3xl font-semibold tracking-[-0.02em] text-[#F5F7FA] sm:text-4xl">
          Bring Structure to Your Futures Analysis.
        </h2>
        <p className="mx-auto mt-4 max-w-2xl text-[15px] leading-relaxed text-mist">
          Explore a more systematic way to monitor futures price behaviour
          around contract-anchored VWAP.
        </p>
        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <Button href="/register" size="lg">
            Get Started
          </Button>
          <Button href="/login" variant="secondary" size="lg">
            Login
          </Button>
        </div>
      </div>
    </section>
  );
}
