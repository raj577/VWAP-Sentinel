import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { LogoMark } from "@/components/ui/icons";

const PRODUCT_LINKS = [
  { href: "#features", label: "Features" },
  { href: "#how-it-works", label: "How It Works" },
  { href: "#strategies", label: "Strategies" },
  { href: "#pricing", label: "Pricing" },
  { href: "#faq", label: "FAQ" },
];

export function Footer() {
  return (
    <footer className="border-t border-white/[0.08] bg-ink2">
      <div className="mx-auto grid w-full max-w-7xl gap-10 px-4 py-14 sm:px-6 md:grid-cols-2 lg:grid-cols-4 lg:px-8">
        <div className="lg:col-span-2">
          <div className="flex items-center gap-2.5">
            <LogoMark size={30} />
            <span className="text-[15px] font-semibold text-[#F5F7FA]">
              AVWAP Scanner
            </span>
          </div>
          <p className="mt-4 max-w-sm text-sm leading-relaxed text-mist">
            Contract-anchored AVWAP analysis for NSE stock futures. Structured
            scanning, immutable scan history and session VWAP context in one
            research dashboard.
          </p>
          <p className="mt-6 max-w-md text-xs leading-relaxed text-mist/80">
            Market analysis tools provide informational insights only. They do
            not guarantee trading outcomes or constitute investment advice.
          </p>
        </div>

        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-mist">
            Product
          </p>
          <ul className="mt-4 space-y-2.5 text-sm">
            {PRODUCT_LINKS.map((link) => (
              <li key={link.href}>
                <a href={link.href} className="text-mist transition-colors hover:text-[#F5F7FA]">
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-mist">
            Account
          </p>
          <ul className="mt-4 space-y-2.5 text-sm">
            <li>
              <Link href="/login" className="text-mist transition-colors hover:text-[#F5F7FA]">
                Login
              </Link>
            </li>
            <li>
              <Link href="/register" className="text-mist transition-colors hover:text-[#F5F7FA]">
                Create account
              </Link>
            </li>
            <li>
              <Link href="/forgot-password" className="text-mist transition-colors hover:text-[#F5F7FA]">
                Forgot password
              </Link>
            </li>
          </ul>

          <p className="mt-6 text-xs font-semibold uppercase tracking-[0.18em] text-mist">
            Legal
          </p>
          <ul className="mt-3 space-y-2.5 text-sm text-mist">
            <li className="flex items-center gap-2">
              Privacy Policy <Badge tone="neutral">Coming soon</Badge>
            </li>
            <li className="flex items-center gap-2">
              Terms of Service <Badge tone="neutral">Coming soon</Badge>
            </li>
            <li className="flex items-center gap-2">
              Contact <Badge tone="neutral">Coming soon</Badge>
            </li>
          </ul>
        </div>
      </div>

      <div className="border-t border-white/[0.08]">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-2 px-4 py-5 text-xs text-mist sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
          <p>© {new Date().getFullYear()} AVWAP Scanner. All rights reserved.</p>
          <p>Built for research. Not investment advice.</p>
        </div>
      </div>
    </footer>
  );
}
