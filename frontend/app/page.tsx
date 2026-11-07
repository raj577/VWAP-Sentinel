import type { Metadata } from "next";

import { FAQSection } from "@/components/landing/FAQSection";
import { FeaturesSection } from "@/components/landing/FeaturesSection";
import { FinalCTA } from "@/components/landing/FinalCTA";
import { HeroSection } from "@/components/landing/HeroSection";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { PricingSection } from "@/components/landing/PricingSection";
import { ScannerPreview } from "@/components/landing/ScannerPreview";
import { StrategySection } from "@/components/landing/StrategySection";
import { WhyChoose } from "@/components/landing/WhyChoose";
import { Footer } from "@/components/layout/Footer";
import { Navbar } from "@/components/layout/Navbar";

export const metadata: Metadata = {
  title: "AVWAP Scanner — Futures Market Intelligence",
  description:
    "Discover futures market setups around contract-anchored VWAP with structured scanning and historical market analysis.",
  openGraph: {
    title: "AVWAP Scanner — Futures Market Intelligence",
    description:
      "Discover futures market setups around contract-anchored VWAP with structured scanning and historical market analysis.",
    siteName: "AVWAP Scanner",
    type: "website",
  },
};

export default function LandingPage() {
  return (
    <>
      <Navbar />
      <main>
        <HeroSection />
        <FeaturesSection />
        <HowItWorks />
        <ScannerPreview />
        <StrategySection />
        <WhyChoose />
        <PricingSection />
        <FAQSection />
        <FinalCTA />
      </main>
      <Footer />
    </>
  );
}
