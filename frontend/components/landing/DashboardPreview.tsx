const CANDLES = [
  { o: 1462, h: 1468, l: 1458, c: 1465 },
  { o: 1465, h: 1471, l: 1463, c: 1468 },
  { o: 1468, h: 1474, l: 1466, c: 1470 },
  { o: 1470, h: 1476, l: 1467, c: 1472 },
  { o: 1472, h: 1478, l: 1469, c: 1470 },
  { o: 1470, h: 1473, l: 1462, c: 1464 },
  { o: 1464, h: 1468, l: 1459, c: 1462 },
  { o: 1462, h: 1467, l: 1458, c: 1466 },
  { o: 1466, h: 1472, l: 1464, c: 1471 },
  { o: 1471, h: 1477, l: 1468, c: 1475 },
  { o: 1475, h: 1480, l: 1472, c: 1477 },
  { o: 1477, h: 1481, l: 1470, c: 1472 },
  { o: 1472, h: 1475, l: 1464, c: 1466 },
  { o: 1466, h: 1470, l: 1463, c: 1469 },
  { o: 1469, h: 1474, l: 1467, c: 1472 },
  { o: 1472, h: 1476, l: 1470, c: 1471 },
  { o: 1471, h: 1474, l: 1468, c: 1470 },
  { o: 1470, h: 1473, l: 1467, c: 1471 },
  { o: 1471, h: 1475, l: 1469, c: 1473 },
  { o: 1473, h: 1477, l: 1470, c: 1472 },
  { o: 1472, h: 1475, l: 1469, c: 1470 },
  { o: 1470, h: 1472, l: 1467, c: 1469 },
  { o: 1469, h: 1471, l: 1466, c: 1468 },
  { o: 1468, h: 1470, l: 1465, c: 1467 },
  { o: 1467, h: 1469, l: 1464, c: 1466 },
  { o: 1466, h: 1468, l: 1463, c: 1465 },
  { o: 1465, h: 1467, l: 1462, c: 1464 },
  { o: 1464, h: 1466, l: 1461, c: 1463 },
  { o: 1463, h: 1465, l: 1460, c: 1462 },
  { o: 1462, h: 1464, l: 1460, c: 1463 },
  { o: 1463, h: 1465, l: 1461, c: 1462 },
  { o: 1462, h: 1465, l: 1460, c: 1464 },
  { o: 1464, h: 1467, l: 1462, c: 1466 },
  { o: 1466, h: 1470, l: 1464, c: 1469 },
];

const AVWAP = [
  1460, 1462, 1464, 1466, 1467, 1466, 1465, 1466, 1468, 1470, 1471, 1470, 1468,
  1467, 1468, 1469, 1469, 1469, 1470, 1470, 1469, 1469, 1468, 1468, 1467, 1467,
  1466, 1466, 1465, 1465, 1465, 1465, 1466, 1467,
];

const VWAP = [
  1458, 1460, 1461, 1463, 1465, 1466, 1464, 1465, 1467, 1469, 1471, 1473, 1471,
  1469, 1470, 1471, 1471, 1471, 1472, 1473, 1473, 1472, 1471, 1471, 1470, 1470,
  1469, 1469, 1468, 1468, 1469, 1469, 1470, 1471,
];

const WIDTH = 860;
const HEIGHT = 330;
const PAD = { left: 8, right: 58, top: 14, bottom: 18 };

export function DashboardPreview() {
  const all = CANDLES.flatMap((candle) => [candle.h, candle.l]);
  const min = Math.min(...all, ...AVWAP, ...VWAP) - 4;
  const max = Math.max(...all, ...AVWAP, ...VWAP) + 4;
  const plotWidth = WIDTH - PAD.left - PAD.right;
  const plotHeight = HEIGHT - PAD.top - PAD.bottom;
  const slot = plotWidth / CANDLES.length;
  const bodyWidth = Math.max(4, Math.min(11, slot * 0.55));
  const highlightStart = CANDLES.length - 5;

  const x = (index: number) => PAD.left + slot * (index + 0.5);
  const y = (price: number) => PAD.top + ((max - price) / (max - min)) * plotHeight;

  const path = (values: number[]) =>
    values
      .map((value, index) => `${index === 0 ? "M" : "L"}${x(index).toFixed(1)},${y(value).toFixed(1)}`)
      .join(" ");

  const latest = CANDLES[CANDLES.length - 1];
  const change = ((latest.c - CANDLES[0].c) / CANDLES[0].c) * 100;

  return (
    <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-[#0A1220]/95 shadow-[0_40px_120px_-50px_rgba(0,0,0,0.95)]">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_80%_0%,rgba(39,224,138,0.12),transparent_55%),radial-gradient(ellipse_at_10%_100%,rgba(54,163,255,0.1),transparent_55%)]"
      />
      <div className="relative flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.08] px-4 py-3 sm:px-5">
        <div className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-mint/[0.12] text-mint">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden>
              <path d="M4 18V6M8 18V9M12 18v-5M16 18V8M20 18v-3" />
            </svg>
          </span>
          <div>
            <p className="font-mono text-[12px] text-[#E9EEF5]">NSE:RELIANCE26NOVFUT</p>
            <p className="text-[10px] uppercase tracking-[0.16em] text-mist">
              Contract-anchored AVWAP
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="font-mono text-lg font-semibold text-[#F5F7FA]">
              1,469.00
            </p>
            <p className="font-mono text-[11px] text-mint">
              +{change.toFixed(2)}% <span className="text-mist">today</span>
            </p>
          </div>
          <span className="rounded-full border border-mint/25 bg-mint/10 px-2.5 py-1 text-[10px] font-medium text-mint">
            AVWAP HUGGING
          </span>
        </div>
      </div>

      <div className="relative px-2 pb-2 pt-3 sm:px-3">
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          className="h-auto w-full"
          role="img"
          aria-label="Illustrative candlestick chart with contract AVWAP and session VWAP"
        >
          {[0.2, 0.4, 0.6, 0.8].map((fraction) => (
            <line
              key={fraction}
              x1={PAD.left}
              x2={WIDTH - PAD.right}
              y1={PAD.top + plotHeight * fraction}
              y2={PAD.top + plotHeight * fraction}
              stroke="rgba(255,255,255,0.05)"
              strokeWidth="1"
            />
          ))}

          <rect
            x={x(highlightStart) - slot / 2}
            y={PAD.top}
            width={slot * 5}
            height={plotHeight}
            fill="#FBBF24"
            opacity="0.07"
          />
          <rect
            x={x(highlightStart) - slot / 2}
            y={PAD.top}
            width={slot * 5}
            height={plotHeight}
            fill="none"
            stroke="rgba(251,191,36,0.25)"
            strokeDasharray="3 4"
          />

          {CANDLES.map((candle, index) => {
            const up = candle.c >= candle.o;
            const color = up ? "#27E08A" : "#F0616D";
            const bodyTop = y(Math.max(candle.o, candle.c));
            const bodyBottom = y(Math.min(candle.o, candle.c));
            return (
              <g key={index}>
                <line
                  x1={x(index)}
                  x2={x(index)}
                  y1={y(candle.h)}
                  y2={y(candle.l)}
                  stroke={color}
                  strokeWidth="1"
                  opacity="0.85"
                />
                <rect
                  x={x(index) - bodyWidth / 2}
                  y={bodyTop}
                  width={bodyWidth}
                  height={Math.max(1.5, bodyBottom - bodyTop)}
                  fill={color}
                  rx="1"
                  opacity={up ? 0.9 : 0.85}
                />
              </g>
            );
          })}

          <path
            d={path(VWAP)}
            fill="none"
            stroke="#36A3FF"
            strokeWidth="1.7"
            className="line-draw"
          />
          <path
            d={path(AVWAP)}
            fill="none"
            stroke="#F0616D"
            strokeWidth="1.9"
            className="line-draw"
          />

          <circle cx={x(AVWAP.length - 1)} cy={y(AVWAP[AVWAP.length - 1])} r="3" fill="#F0616D" />
          <circle cx={x(VWAP.length - 1)} cy={y(VWAP[VWAP.length - 1])} r="3" fill="#36A3FF" />

          <text
            x={WIDTH - PAD.right + 8}
            y={y(AVWAP[AVWAP.length - 1]) + 3}
            fontSize="10"
            fill="#F0616D"
          >
            AVWAP
          </text>
          <text
            x={WIDTH - PAD.right + 8}
            y={y(VWAP[VWAP.length - 1]) + 3}
            fontSize="10"
            fill="#36A3FF"
          >
            VWAP
          </text>
        </svg>
      </div>

      <div className="relative flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-white/[0.08] px-4 py-2.5 text-[10px] text-mist sm:px-5">
        <span className="flex items-center gap-1.5">
          <span className="h-0.5 w-4 rounded bg-[#F0616D]" /> Contract AVWAP
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-0.5 w-4 rounded bg-[#36A3FF]" /> Session VWAP
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm border border-amber-400/40 bg-amber-400/10" />
          Consolidation window
        </span>
        <span className="ml-auto text-mist/70">Illustrative preview</span>
      </div>
    </div>
  );
}
