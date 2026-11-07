import type { ReactNode } from "react";

type Tone = "mint" | "sky" | "amber" | "neutral";

const TONES: Record<Tone, string> = {
  mint: "border-mint/25 bg-mint/10 text-mint",
  sky: "border-sky/25 bg-sky/10 text-sky",
  amber: "border-amber-400/25 bg-amber-400/10 text-amber-300",
  neutral: "border-white/10 bg-white/5 text-mist",
};

export function Badge({
  children,
  tone = "neutral",
  className = "",
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <span
      className={[
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5",
        "text-[11px] font-medium tracking-wide",
        TONES[tone],
        className,
      ].join(" ")}
    >
      {children}
    </span>
  );
}
