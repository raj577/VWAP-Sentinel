"use client";

import { useState } from "react";

import { ChevronDown } from "@/components/ui/icons";

const FAQS = [
  {
    question: "What is contract-anchored AVWAP?",
    answer:
      "It is a volume-weighted average price anchored to the first available candle of a specific futures contract and carried forward for that contract's life. It does not reset at session boundaries.",
  },
  {
    question: "How is it different from regular session VWAP?",
    answer:
      "Session VWAP resets every trading day and reflects the current session's average. Contract AVWAP reflects the contract's full history, so the two lines answer different questions. The scanner uses contract AVWAP as the primary reference and session VWAP as context.",
  },
  {
    question: "Which instruments does the scanner monitor?",
    answer:
      "Active NSE stock futures discovered from the exchange symbol master. Each expiry is treated as a separate contract so data is never mixed across expiries.",
  },
  {
    question: "How frequently is the scanner updated?",
    answer:
      "The platform refreshes market data on a configurable schedule, with 56 minutes as the default. Administrators can also trigger a manual refresh. Scan snapshots are timestamped and immutable.",
  },
  {
    question: "Do I need my own FYERS account?",
    answer:
      "No. Market data is centralised by the platform. Customers sign in with their own platform account and never provide FYERS credentials.",
  },
  {
    question: "Does the scanner place trades automatically?",
    answer:
      "No. The platform is research software. It does not place orders, connect to a broker for execution, or provide investment advice.",
  },
  {
    question: "Can I view historical scan results?",
    answer:
      "Yes. Each completed scan is stored as a separate snapshot, and the history view can compare runs and show first or latest appearances for a symbol.",
  },
];

export function FAQSection() {
  const [open, setOpen] = useState<number | null>(0);

  return (
    <section id="faq" className="relative scroll-mt-24 py-20 sm:py-24">
      <div className="mx-auto grid w-full max-w-7xl gap-10 px-4 sm:px-6 lg:grid-cols-[0.8fr_1.2fr] lg:px-8">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-mint">
            FAQ
          </p>
          <h2 className="mt-3 text-3xl font-semibold tracking-[-0.02em] text-[#F5F7FA] sm:text-4xl">
            Questions, Answered.
          </h2>
          <p className="mt-4 text-sm leading-relaxed text-mist">
            The product is a structured market-analysis tool. These answers
            describe how it works, not what it promises.
          </p>
        </div>

        <div className="divide-y divide-white/[0.08] rounded-2xl border border-white/[0.08] bg-card/60">
          {FAQS.map((faq, index) => {
            const expanded = open === index;
            return (
              <div key={faq.question}>
                <h3>
                  <button
                    type="button"
                    aria-expanded={expanded}
                    aria-controls={`faq-panel-${index}`}
                    id={`faq-button-${index}`}
                    onClick={() => setOpen(expanded ? null : index)}
                    className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left text-[14px] font-medium text-[#F5F7FA] transition-colors hover:bg-white/[0.02]"
                  >
                    {faq.question}
                    <ChevronDown
                      size={17}
                      className={`flex-none text-mist transition-transform duration-200 ${
                        expanded ? "rotate-180" : ""
                      }`}
                    />
                  </button>
                </h3>
                <div
                  id={`faq-panel-${index}`}
                  role="region"
                  aria-labelledby={`faq-button-${index}`}
                  hidden={!expanded}
                  className="px-5 pb-4 text-[13px] leading-relaxed text-mist"
                >
                  {faq.answer}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
