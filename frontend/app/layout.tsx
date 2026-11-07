import type { Metadata } from "next";
import { Inter } from "next/font/google";

import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "AVWAP Scanner — Futures Market Intelligence",
  description:
    "Discover futures market setups around contract-anchored VWAP with structured scanning and historical market analysis.",
  applicationName: "AVWAP Scanner",
  openGraph: {
    title: "AVWAP Scanner — Futures Market Intelligence",
    description:
      "Discover futures market setups around contract-anchored VWAP with structured scanning and historical market analysis.",
    siteName: "AVWAP Scanner",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "AVWAP Scanner — Futures Market Intelligence",
    description:
      "Contract-anchored AVWAP scanning for NSE stock futures.",
  },
  robots: { index: true, follow: true },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="min-h-screen bg-ink font-sans text-[#F5F7FA]">
        {children}
      </body>
    </html>
  );
}
