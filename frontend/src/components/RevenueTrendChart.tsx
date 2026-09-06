import type { RevenueTrendPoint } from "../types/admin";
import { formatMoney } from "../utils/format";

const WIDTH = 720;
const HEIGHT = 220;
const PADDING_BOTTOM = 28;
const PADDING_TOP = 10;

export function RevenueTrendChart({ data }: { data: RevenueTrendPoint[] }) {
  if (data.length === 0) return null;

  const values = data.map((d) => Number(d.revenue));
  const max = Math.max(...values, 1);
  const chartHeight = HEIGHT - PADDING_BOTTOM - PADDING_TOP;
  const barWidth = WIDTH / data.length;
  const labelEvery = Math.max(1, Math.ceil(data.length / 7));

  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      className="revenue-svg"
      role="img"
      aria-label="Daily revenue trend"
    >
      {data.map((point, i) => {
        const value = Number(point.revenue);
        const barHeight = (value / max) * chartHeight;
        const x = i * barWidth + barWidth * 0.15;
        const y = PADDING_TOP + (chartHeight - barHeight);
        const w = barWidth * 0.7;
        return (
          <g key={point.date}>
            <rect
              x={x}
              y={y}
              width={w}
              height={Math.max(barHeight, 1)}
              rx={2}
              className="revenue-svg__bar"
            >
              <title>
                {point.date}: {formatMoney(point.revenue)} ({point.orders} order
                {point.orders === 1 ? "" : "s"})
              </title>
            </rect>
            {i % labelEvery === 0 && (
              <text
                x={x + w / 2}
                y={HEIGHT - 8}
                textAnchor="middle"
                className="revenue-svg__label"
              >
                {new Date(point.date).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}
