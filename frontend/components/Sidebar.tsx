"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { ChevronDown, LogoMark, Menu, Close } from "@/components/ui/icons";

interface NavItem {
  href: string;
  label: string;
}

interface NavGroup {
  label: string;
  items: NavItem[];
  adminOnly?: boolean;
}

const CUSTOMER_GROUPS: NavGroup[] = [
  {
    label: "Main",
    items: [
      { href: "/dashboard", label: "Overview" },
      { href: "/dashboard/scanner", label: "Current Scanner" },
      { href: "/dashboard/history", label: "Scan History" },
      { href: "/dashboard/watchlist", label: "Watchlist" },
      { href: "/dashboard/strategies", label: "Strategies" },
    ],
  },
  {
    label: "Account",
    items: [
      { href: "/dashboard/subscription", label: "Subscription" },
      { href: "/dashboard/billing", label: "Billing" },
      { href: "/dashboard/profile", label: "Profile" },
      { href: "/dashboard/security", label: "Security" },
    ],
  },
];

const ADMIN_GROUPS: NavGroup[] = [
  {
    label: "Overview",
    items: [{ href: "/admin", label: "Dashboard" }],
    adminOnly: true,
  },
  {
    label: "Market Operations",
    items: [
      { href: "/admin/market-data", label: "Market Data" },
      { href: "/admin/scheduler", label: "Scheduler" },
      { href: "/admin/jobs", label: "Pipeline Jobs" },
      { href: "/admin/scanner", label: "Scanner Configuration" },
      { href: "/admin/scan-history", label: "Scan History" },
    ],
    adminOnly: true,
  },
  {
    label: "Customers",
    items: [
      { href: "/admin/users", label: "Users" },
      { href: "/admin/roles", label: "Roles & Permissions" },
    ],
    adminOnly: true,
  },
  {
    label: "Monetization",
    items: [
      { href: "/admin/plans", label: "Subscription Plans" },
      { href: "/admin/trials", label: "Trial Management" },
      { href: "/admin/entitlements", label: "Entitlements" },
      { href: "/admin/payments", label: "Payments" },
    ],
    adminOnly: true,
  },
  {
    label: "Platform",
    items: [
      { href: "/admin/feature-flags", label: "Feature Flags" },
      { href: "/admin/audit-logs", label: "Audit Logs" },
      { href: "/admin/settings", label: "Settings" },
    ],
    adminOnly: true,
  },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/dashboard" || href === "/admin") return pathname === href;
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function Sidebar({ roles }: { roles: string[] }) {
  const pathname = usePathname();
  const admin = roles.some((role) => role === "ADMIN" || role === "SUPER_ADMIN");
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [closedGroups, setClosedGroups] = useState<Record<string, boolean>>({});

  const groups = [...CUSTOMER_GROUPS, ...(admin ? ADMIN_GROUPS : [])];

  function toggleGroup(label: string) {
    setClosedGroups((value) => ({ ...value, [label]: !value[label] }));
  }

  return (
    <>
      <div className="flex items-center justify-between border-b border-white/[0.06] bg-[#0B1220] px-4 py-3 md:hidden">
        <Link href="/dashboard" className="flex items-center gap-2">
          <LogoMark size={26} />
          <span className="text-sm font-semibold text-[#F5F7FA]">AVWAP Scanner</span>
        </Link>
        <button
          type="button"
          aria-label={mobileOpen ? "Close navigation" : "Open navigation"}
          aria-expanded={mobileOpen}
          onClick={() => setMobileOpen((value) => !value)}
          className="rounded-lg border border-white/10 p-2 text-mist"
        >
          {mobileOpen ? <Close size={18} /> : <Menu size={18} />}
        </button>
      </div>

      <aside
        className={[
          "flex-col gap-5 border-r border-white/[0.06] bg-[#0B1220] px-3 py-5",
          "md:flex md:h-screen md:shrink-0",
          collapsed ? "md:w-[74px]" : "md:w-64",
          mobileOpen ? "flex" : "hidden md:flex",
        ].join(" ")}
      >
        <div className={`hidden items-center gap-2.5 px-2 md:flex ${collapsed ? "justify-center" : ""}`}>
          <LogoMark size={28} />
          {!collapsed ? (
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-[#F5F7FA]">AVWAP Scanner</p>
              <p className="text-[10px] uppercase tracking-[0.16em] text-mist">
                {admin ? "Admin console" : "Research workspace"}
              </p>
            </div>
          ) : null}
        </div>

        <button
          type="button"
          onClick={() => setCollapsed((value) => !value)}
          className="hidden items-center justify-center rounded-lg border border-white/10 py-1.5 text-[10px] text-mist hover:text-white md:flex"
        >
          {collapsed ? "»" : "« Collapse"}
        </button>

        <nav
          aria-label="Application"
          className="flex max-h-[calc(100vh-170px)] flex-col gap-4 overflow-y-auto pb-2"
        >
          {groups.map((group) => {
            if (group.adminOnly && !admin) return null;
            const closed = closedGroups[group.label];
            return (
              <div key={group.label}>
                {!collapsed ? (
                  <button
                    type="button"
                    onClick={() => toggleGroup(group.label)}
                    aria-expanded={!closed}
                    className="mb-1 flex w-full items-center justify-between px-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-mist/70"
                  >
                    {group.label}
                    <ChevronDown
                      size={12}
                      className={`transition-transform ${closed ? "-rotate-90" : ""}`}
                    />
                  </button>
                ) : null}
                {!closed ? (
                  <ul className="space-y-0.5">
                    {group.items.map((item) => {
                      const active = isActive(pathname, item.href);
                      return (
                        <li key={item.href}>
                          <Link
                            href={item.href}
                            onClick={() => setMobileOpen(false)}
                            title={collapsed ? item.label : undefined}
                            className={[
                              "block rounded-lg px-3 py-2 text-[13px] transition-colors",
                              active
                                ? "bg-mint/10 text-mint"
                                : "text-mist hover:bg-white/[0.04] hover:text-[#F5F7FA]",
                              collapsed ? "text-center" : "",
                            ].join(" ")}
                          >
                            {collapsed ? item.label.slice(0, 2) : item.label}
                          </Link>
                        </li>
                      );
                    })}
                  </ul>
                ) : null}
              </div>
            );
          })}
        </nav>

        {!collapsed ? (
          <p className="mt-auto hidden px-2 text-[10px] leading-relaxed text-mist/60 md:block">
            Research tools only. No order placement or investment advice.
          </p>
        ) : null}
      </aside>
    </>
  );
}
