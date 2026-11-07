import type { ReactNode } from "react";

export function Card({
  children,
  className = "",
  as: Tag = "div",
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "section" | "article";
}) {
  return (
    <Tag
      className={[
        "rounded-2xl border border-white/[0.08] card-sheen",
        "shadow-[0_18px_50px_-30px_rgba(0,0,0,0.9)]",
        className,
      ].join(" ")}
    >
      {children}
    </Tag>
  );
}
