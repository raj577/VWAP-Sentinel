const TONES: Record<string, string> = {
  COMPLETED: "border-mint/25 bg-mint/10 text-mint",
  ACTIVE: "border-mint/25 bg-mint/10 text-mint",
  CONNECTED: "border-mint/25 bg-mint/10 text-mint",
  RUNNING: "border-sky/25 bg-sky/10 text-sky",
  PENDING: "border-sky/25 bg-sky/10 text-sky",
  PARTIALLY_COMPLETED: "border-amber-400/25 bg-amber-400/10 text-amber-300",
  AUTHENTICATION_EXPIRED: "border-amber-400/25 bg-amber-400/10 text-amber-300",
  AUTHENTICATION_FAILED: "border-red-500/25 bg-red-500/10 text-red-300",
  FAILED: "border-red-500/25 bg-red-500/10 text-red-300",
  SUSPENDED: "border-red-500/25 bg-red-500/10 text-red-300",
  DISABLED: "border-white/10 bg-white/5 text-mist",
  CANCELLED: "border-white/10 bg-white/5 text-mist",
  PENDING_VERIFICATION: "border-amber-400/25 bg-amber-400/10 text-amber-300",
  NOT_CONFIGURED: "border-white/10 bg-white/5 text-mist",
  API_UNAVAILABLE: "border-amber-400/25 bg-amber-400/10 text-amber-300",
};

export function StatusBadge({ status }: { status: string }) {
  const tone = TONES[status] ?? "border-white/10 bg-white/5 text-mist";
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${tone}`}
    >
      {status.replaceAll("_", " ")}
    </span>
  );
}
