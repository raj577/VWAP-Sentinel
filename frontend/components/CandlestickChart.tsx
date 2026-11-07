import type { ChartPoint } from "@/types/api";

const WIDTH = 1000;
const HEIGHT = 430;
const PAD = { left: 62, right: 16, top: 16, bottom: 30 };

function timeLabel(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("en-IN", {
    timeZone: "Asia/Kolkata",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function CandlestickChart({
  points,
  patternStart,
  patternEnd,
}: {
  points: ChartPoint[];
  patternStart: string | null;
  patternEnd: string | null;
}) {
  if (points.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-panel p-6 text-sm text-muted">
        No candles available for this chart.
      </div>
    );
  }

  const prices: number[] = [];
  for (const point of points) {
    prices.push(point.high, point.low);
    if (point.avwap !== null) prices.push(point.avwap);
    if (point.session_vwap !== null) prices.push(point.session_vwap);
  }
  const rawMin = Math.min(...prices);
  const rawMax = Math.max(...prices);
  const span = rawMax - rawMin || 1;
  const min = rawMin - span * 0.04;
  const max = rawMax + span * 0.04;

  const plotWidth = WIDTH - PAD.left - PAD.right;
  const plotHeight = HEIGHT - PAD.top - PAD.bottom;
  const slot = plotWidth / points.length;
  const candleWidth = Math.max(2, Math.min(12, slot * 0.62));

  const x = (index: number) => PAD.left + slot * (index + 0.5);
  const y = (price: number) =>
    PAD.top + ((max - price) / (max - min)) * plotHeight;

  const patternStartMs = patternStart ? Date.parse(patternStart) : null;
  const patternEndMs = patternEnd ? Date.parse(patternEnd) : null;
  const inPattern = (value: string) => {
    const ms = Date.parse(value);
    if (Number.isNaN(ms) || patternStartMs === null || patternEndMs === null) {
      return false;
    }
    return ms >= patternStartMs && ms <= patternEndMs;
  };

  const linePath = (key: "avwap" | "session_vwap") => {
    const commands: string[] = [];
    let drawing = false;
    points.forEach((point, index) => {
      const value = point[key];
      if (value === null || !Number.isFinite(value)) {
        drawing = false;
        return;
      }
      commands.push(`${drawing ? "L" : "M"}${x(index).toFixed(1)},${y(value).toFixed(1)}`);
      drawing = true;
    });
    return commands.join(" ");
  };

  const yTicks = 4;
  const gridPrices = Array.from(
    { length: yTicks + 1 },
    (_, index) => min + ((max - min) * index) / yTicks,
  );

  return (
    <div className="rounded-lg border border-border bg-panel p-3">
      <div className="mb-2 flex flex-wrap items-center gap-4 text-xs text-muted">
        <span className="flex items-center gap-1">
          <span className="inline-block h-0.5 w-4 bg-[#ff3b30]" /> Contract AVWAP
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-0.5 w-4 bg-[#2f80ed]" /> Session VWAP
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-3 w-3 bg-amber-400/20 ring-1 ring-amber-400/40" />{" "}
          Detected pattern
        </span>
      </div>
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="h-auto w-full"
        role="img"
        aria-label="1-hour candlestick chart with AVWAP and VWAP"
      >
        {gridPrices.map((price) => (
          <g key={price}>
            <line
              x1={PAD.left}
              x2={WIDTH - PAD.right}
              y1={y(price)}
              y2={y(price)}
              stroke="#26303d"
              strokeWidth="1"
            />
            <text
              x={PAD.left - 6}
              y={y(price) + 3}
              textAnchor="end"
              fontSize="10"
              fill="#8b98a9"
            >
              {price.toFixed(1)}
            </text>
          </g>
        ))}

        {points.map((point, index) =>
          inPattern(point.timestamp) ? (
            <rect
              key={`hl-${point.timestamp}`}
              x={x(index) - slot / 2}
              y={PAD.top}
              width={slot}
              height={plotHeight}
              fill="#fbbf24"
              opacity="0.12"
            />
          ) : null,
        )}

        {points.map((point, index) => {
          const up = point.close >= point.open;
          const colour = up ? "#26a69a" : "#ef5350";
          const bodyTop = y(Math.max(point.open, point.close));
          const bodyBottom = y(Math.min(point.open, point.close));
          const bodyHeight = Math.max(1, bodyBottom - bodyTop);
          return (
            <g key={`candle-${point.timestamp}`}>
              <line
                x1={x(index)}
                x2={x(index)}
                y1={y(point.high)}
                y2={y(point.low)}
                stroke={colour}
                strokeWidth="1"
              />
              <rect
                x={x(index) - candleWidth / 2}
                y={bodyTop}
                width={candleWidth}
                height={bodyHeight}
                fill={colour}
              />
            </g>
          );
        })}

        <path d={linePath("avwap")} fill="none" stroke="#ff3b30" strokeWidth="1.6" />
        <path
          d={linePath("session_vwap")}
          fill="none"
          stroke="#2f80ed"
          strokeWidth="1.4"
        />

        <text
          x={PAD.left}
          y={HEIGHT - 8}
          fontSize="10"
          fill="#8b98a9"
        >
          {timeLabel(points[0].timestamp)}
        </text>
        <text
          x={WIDTH - PAD.right}
          y={HEIGHT - 8}
          textAnchor="end"
          fontSize="10"
          fill="#8b98a9"
        >
          {timeLabel(points[points.length - 1].timestamp)}
        </text>
      </svg>
    </div>
  );
}
