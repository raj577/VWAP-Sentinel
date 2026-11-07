import Link from "next/link";

export function AuthShell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-base p-6">
      <div className="w-full max-w-md rounded-xl border border-border bg-panel p-6 shadow-xl">
        <Link
          href="/login"
          className="text-xs uppercase tracking-[0.2em] text-muted hover:text-white"
        >
          VWAP Sentinel
        </Link>
        <h1 className="mt-3 text-xl font-semibold text-white">{title}</h1>
        {subtitle ? <p className="mt-1 text-sm text-muted">{subtitle}</p> : null}
        <div className="mt-6">{children}</div>
        {footer ? <div className="mt-5 text-xs text-muted">{footer}</div> : null}
      </div>
    </main>
  );
}
