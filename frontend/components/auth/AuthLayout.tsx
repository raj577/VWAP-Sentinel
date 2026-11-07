import Link from "next/link";
import type { ReactNode } from "react";

import { LogoMark } from "@/components/ui/icons";

function AuthChart() {
  return (
    <svg
      viewBox="0 0 520 260"
      className="h-auto w-full"
      role="img"
      aria-label="Illustrative AVWAP chart"
    >
      <defs>
        <linearGradient id="auth-area" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#27E08A" stopOpacity="0.16" />
          <stop offset="100%" stopColor="#27E08A" stopOpacity="0" />
        </linearGradient>
      </defs>
      {[0.2, 0.4, 0.6, 0.8].map((fraction) => (
        <line
          key={fraction}
          x1="10"
          x2="510"
          y1={20 + 210 * fraction}
          y2={20 + 210 * fraction}
          stroke="rgba(255,255,255,0.05)"
          strokeWidth="1"
        />
      ))}
      <path
        d="M10 175 C60 168, 75 150, 110 148 C150 145, 160 168, 195 162 C235 155, 245 128, 285 132 C325 136, 335 160, 370 150 C410 138, 425 112, 465 118 C490 121, 500 108, 510 104 L510 230 L10 230 Z"
        fill="url(#auth-area)"
      />
      <path
        d="M10 175 C60 168, 75 150, 110 148 C150 145, 160 168, 195 162 C235 155, 245 128, 285 132 C325 136, 335 160, 370 150 C410 138, 425 112, 465 118 C490 121, 500 108, 510 104"
        fill="none"
        stroke="#27E08A"
        strokeWidth="2"
        className="line-draw"
      />
      <path
        d="M10 150 C80 148, 120 140, 170 143 C220 146, 250 150, 300 145 C350 140, 390 128, 440 132 C470 134, 495 128, 510 126"
        fill="none"
        stroke="#36A3FF"
        strokeWidth="1.6"
        strokeDasharray="5 4"
        opacity="0.8"
      />
      <path
        d="M10 190 C70 188, 110 182, 160 184 C210 186, 240 182, 290 186 C340 190, 380 180, 430 184 C470 187, 495 182, 510 184"
        fill="none"
        stroke="#F0616D"
        strokeWidth="1.6"
        opacity="0.9"
      />
      <circle cx="465" cy="118" r="4" fill="#27E08A" />
    </svg>
  );
}

export function AuthLayout({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <main className="relative min-h-screen overflow-hidden bg-ink">
      <div aria-hidden className="pointer-events-none absolute inset-0 hero-glow opacity-70" />
      <div aria-hidden className="pointer-events-none absolute inset-0 grid-fade opacity-40" />

      <div className="relative mx-auto grid min-h-screen w-full max-w-7xl lg:grid-cols-2">
        <section className="hidden flex-col justify-between px-10 py-12 lg:flex xl:px-14">
          <Link href="/" className="flex items-center gap-2.5">
            <LogoMark size={32} />
            <span className="text-[15px] font-semibold text-[#F5F7FA]">
              AVWAP Scanner
            </span>
          </Link>

          <div className="max-w-lg">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-mint">
              Futures market intelligence
            </p>
            <h1 className="mt-4 text-balance text-4xl font-semibold leading-[1.1] tracking-[-0.03em] text-[#F5F7FA] xl:text-[44px]">
              Find the setup.
              <br />
              <span className="bg-gradient-to-r from-mint to-sky bg-clip-text text-transparent">
                Before the move.
              </span>
            </h1>
            <p className="mt-5 text-[15px] leading-relaxed text-mist">
              Precision futures analytics powered by contract-anchored VWAP,
              session VWAP context and structured scan history.
            </p>

            <div className="mt-10 rounded-2xl border border-white/[0.08] bg-card/50 p-5">
              <div className="mb-3 flex items-center justify-between text-[11px] text-mist">
                <span className="font-mono">NSE:RELIANCE26NOVFUT</span>
                <span className="rounded-full border border-mint/25 bg-mint/10 px-2 py-0.5 text-mint">
                  AVWAP HUGGING
                </span>
              </div>
              <AuthChart />
              <div className="mt-3 flex items-center gap-4 text-[10px] text-mist">
                <span className="flex items-center gap-1.5">
                  <span className="h-0.5 w-3 bg-mint" /> Contract AVWAP
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-0.5 w-3 bg-sky" /> Session VWAP
                </span>
                <span className="ml-auto text-mist/60">Illustrative</span>
              </div>
            </div>
          </div>

          <p className="max-w-md text-[11px] leading-relaxed text-mist/70">
            Market analysis tools provide informational insights only. They do
            not guarantee trading outcomes or constitute investment advice.
          </p>
        </section>

        <section className="flex min-h-screen flex-col justify-center px-4 py-10 sm:px-8 lg:px-10">
          <div className="mx-auto w-full max-w-md">
            <div className="mb-8 flex items-center justify-between lg:hidden">
              <Link href="/" className="flex items-center gap-2">
                <LogoMark size={28} />
                <span className="text-sm font-semibold text-[#F5F7FA]">
                  AVWAP Scanner
                </span>
              </Link>
              <Link href="/" className="text-xs text-mist hover:text-[#F5F7FA]">
                Home
              </Link>
            </div>

            <div className="rounded-2xl border border-white/10 bg-card/80 p-6 shadow-[0_30px_90px_-50px_rgba(0,0,0,0.95)] backdrop-blur sm:p-8">
              <h2 className="text-2xl font-semibold tracking-[-0.02em] text-[#F5F7FA]">
                {title}
              </h2>
              <p className="mt-2 text-sm leading-relaxed text-mist">{subtitle}</p>
              <div className="mt-7">{children}</div>
            </div>

            {footer ? <div className="mt-5 text-center text-xs text-mist">{footer}</div> : null}

            <p className="mt-6 text-center text-[11px] text-mist/60">
              <Link href="/" className="hover:text-mist">
                ← Back to home
              </Link>
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}
