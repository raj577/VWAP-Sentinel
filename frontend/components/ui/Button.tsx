import Link from "next/link";
import type { ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "soft";
type Size = "sm" | "md" | "lg";

const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-mint text-[#04120b] shadow-[0_12px_30px_-12px_rgba(39,224,138,0.65)] hover:bg-[#3bf19c] active:translate-y-px",
  secondary:
    "border border-white/[0.12] bg-white/[0.02] text-[#F5F7FA] hover:border-white/25 hover:bg-white/[0.06]",
  ghost: "text-mist hover:text-[#F5F7FA]",
  soft: "bg-white/[0.06] text-[#F5F7FA] hover:bg-white/[0.1]",
};

const SIZES: Record<Size, string> = {
  sm: "h-9 px-3.5 text-xs",
  md: "h-11 px-5 text-sm",
  lg: "h-12 px-6 text-[15px]",
};

interface BaseProps {
  children: ReactNode;
  variant?: Variant;
  size?: Size;
  className?: string;
}

export function buttonClasses({
  variant = "primary",
  size = "md",
  className = "",
}: Omit<BaseProps, "children">): string {
  return [
    "inline-flex items-center justify-center gap-2 rounded-xl font-medium",
    "transition-all duration-200 focus-visible:outline-none focus-visible:ring-2",
    "focus-visible:ring-mint/60 focus-visible:ring-offset-2 focus-visible:ring-offset-ink",
    "disabled:cursor-not-allowed disabled:opacity-50",
    VARIANTS[variant],
    SIZES[size],
    className,
  ].join(" ");
}

export function Button({
  children,
  variant = "primary",
  size = "md",
  className,
  href,
  ...rest
}: BaseProps &
  React.ButtonHTMLAttributes<HTMLButtonElement> & { href?: string }) {
  if (href) {
    return (
      <Link
        href={href}
        className={buttonClasses({ variant, size, className })}
        onClick={rest.onClick as React.MouseEventHandler<HTMLAnchorElement> | undefined}
      >
        {children}
      </Link>
    );
  }
  return (
    <button
      className={buttonClasses({ variant, size, className })}
      {...rest}
    >
      {children}
    </button>
  );
}
