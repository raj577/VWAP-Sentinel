"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { buttonClasses, Button } from "@/components/ui/Button";
import { Close, LogoMark, Menu } from "@/components/ui/icons";

const NAV_LINKS = [
  { href: "#features", label: "Features" },
  { href: "#how-it-works", label: "How It Works" },
  { href: "#strategies", label: "Strategies" },
  { href: "#pricing", label: "Pricing" },
];

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <header
      className={[
        "fixed inset-x-0 top-0 z-50 transition-all duration-300",
        scrolled || open
          ? "border-b border-white/[0.08] glass"
          : "border-b border-transparent bg-transparent",
      ].join(" ")}
    >
      <div className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-2.5">
          <LogoMark size={30} />
          <span className="text-[15px] font-semibold tracking-tight text-[#F5F7FA]">
            AVWAP Scanner
          </span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex" aria-label="Primary">
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="rounded-lg px-3.5 py-2 text-sm text-mist transition-colors hover:bg-white/5 hover:text-[#F5F7FA]"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-2 md:flex">
          <Link href="/login" className={buttonClasses({ variant: "ghost", size: "sm" })}>
            Login
          </Link>
          <Button href="/register" size="sm">
            Get Started
          </Button>
        </div>

        <button
          type="button"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          aria-controls="mobile-nav"
          onClick={() => setOpen((value) => !value)}
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-white/10 text-[#F5F7FA] md:hidden"
        >
          {open ? <Close size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {open ? (
        <div id="mobile-nav" className="border-t border-white/[0.08] px-4 pb-6 pt-3 md:hidden">
          <nav className="flex flex-col gap-1" aria-label="Mobile">
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className="rounded-lg px-3 py-2.5 text-sm text-mist hover:bg-white/5 hover:text-[#F5F7FA]"
              >
                {link.label}
              </a>
            ))}
          </nav>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <Link
              href="/login"
              onClick={() => setOpen(false)}
              className={buttonClasses({ variant: "secondary", size: "md" })}
            >
              Login
            </Link>
            <Link
              href="/register"
              onClick={() => setOpen(false)}
              className={buttonClasses({ variant: "primary", size: "md" })}
            >
              Get Started
            </Link>
          </div>
        </div>
      ) : null}
    </header>
  );
}
