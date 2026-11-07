import { formatCount, formatDateTime } from "@/lib/format";
import type { Instrument } from "@/types/api";

export function InstrumentsTable({ instruments }: { instruments: Instrument[] }) {
  if (instruments.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-panel p-6 text-sm text-muted">
        No instruments stored yet. Ingestion runs from the backend worker.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border bg-panel">
      <table className="min-w-full divide-y divide-border text-sm">
        <thead className="text-left text-xs uppercase tracking-wide text-muted">
          <tr>
            <th className="px-4 py-3">Symbol</th>
            <th className="px-4 py-3">Underlying</th>
            <th className="px-4 py-3">Expiry</th>
            <th className="px-4 py-3">Lot</th>
            <th className="px-4 py-3">First candle</th>
            <th className="px-4 py-3">Active</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {instruments.map((instrument) => (
            <tr key={instrument.id} className="hover:bg-white/[0.02]">
              <td className="px-4 py-3 font-mono text-xs text-white">
                {instrument.fyers_symbol}
              </td>
              <td className="px-4 py-3 text-muted">
                {instrument.underlying_symbol}
              </td>
              <td className="px-4 py-3 text-muted">{instrument.expiry_date}</td>
              <td className="px-4 py-3 text-muted">
                {formatCount(instrument.lot_size)}
              </td>
              <td className="px-4 py-3 text-muted">
                {formatDateTime(instrument.first_available_timestamp)}
              </td>
              <td className="px-4 py-3">
                <span
                  className={`rounded px-2 py-0.5 text-xs ${
                    instrument.is_active
                      ? "bg-emerald-500/10 text-emerald-300"
                      : "bg-white/5 text-muted"
                  }`}
                >
                  {instrument.is_active ? "active" : "inactive"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
