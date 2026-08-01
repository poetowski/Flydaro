export interface CreditsChartPoint {
  date: Date;
  balance: number;
}

interface CreditsChartProps {
  points: CreditsChartPoint[];
}

const WIDTH = 640;
const HEIGHT = 220;
const PAD_LEFT = 48;
const PAD_RIGHT = 12;
const PAD_TOP = 12;
const PAD_BOTTOM = 24;

function formatShortDate(date: Date): string {
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function CreditsChart({ points }: CreditsChartProps) {
  if (points.length < 2) {
    return <p className="muted">Not enough history yet -- come back after a few transactions.</p>;
  }

  const balances = points.map((p) => p.balance);
  const minBalance = Math.min(...balances);
  const maxBalance = Math.max(...balances);
  // Flat series (e.g. only the signup bonus plus one unrelated entry) would
  // divide by zero -- pad the range so the line still renders, not just a
  // flat edge.
  const balanceRange = maxBalance - minBalance || 1;

  const minTime = points[0].date.getTime();
  const maxTime = points[points.length - 1].date.getTime();
  const timeRange = maxTime - minTime || 1;

  const plotWidth = WIDTH - PAD_LEFT - PAD_RIGHT;
  const plotHeight = HEIGHT - PAD_TOP - PAD_BOTTOM;

  const xFor = (date: Date) => PAD_LEFT + ((date.getTime() - minTime) / timeRange) * plotWidth;
  const yFor = (balance: number) =>
    PAD_TOP + plotHeight - ((balance - minBalance) / balanceRange) * plotHeight;

  const linePath = points
    .map((p, i) => `${i === 0 ? "M" : "L"}${xFor(p.date).toFixed(1)},${yFor(p.balance).toFixed(1)}`)
    .join(" ");
  const areaPath =
    `${linePath} L${xFor(points[points.length - 1].date).toFixed(1)},${(PAD_TOP + plotHeight).toFixed(1)} ` +
    `L${xFor(points[0].date).toFixed(1)},${(PAD_TOP + plotHeight).toFixed(1)} Z`;

  const midIndex = Math.floor((points.length - 1) / 2);

  return (
    <svg
      className="credits-chart"
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      role="img"
      aria-label="Wallet balance over time"
    >
      <line
        x1={PAD_LEFT}
        y1={PAD_TOP}
        x2={PAD_LEFT}
        y2={PAD_TOP + plotHeight}
        stroke="var(--border)"
      />
      <line
        x1={PAD_LEFT}
        y1={PAD_TOP + plotHeight}
        x2={WIDTH - PAD_RIGHT}
        y2={PAD_TOP + plotHeight}
        stroke="var(--border)"
      />

      <path d={areaPath} fill="var(--accent)" opacity={0.15} stroke="none" />
      <path d={linePath} fill="none" stroke="var(--accent)" strokeWidth={2} />

      <text x={4} y={yFor(maxBalance) + 4} fontSize={11} fill="var(--text-muted)">
        {Math.round(maxBalance)}
      </text>
      <text x={4} y={yFor(minBalance) + 4} fontSize={11} fill="var(--text-muted)">
        {Math.round(minBalance)}
      </text>

      <text x={xFor(points[0].date)} y={HEIGHT - 4} fontSize={11} fill="var(--text-muted)">
        {formatShortDate(points[0].date)}
      </text>
      <text
        x={xFor(points[midIndex].date)}
        y={HEIGHT - 4}
        fontSize={11}
        fill="var(--text-muted)"
        textAnchor="middle"
      >
        {formatShortDate(points[midIndex].date)}
      </text>
      <text
        x={xFor(points[points.length - 1].date)}
        y={HEIGHT - 4}
        fontSize={11}
        fill="var(--text-muted)"
        textAnchor="end"
      >
        {formatShortDate(points[points.length - 1].date)}
      </text>
    </svg>
  );
}
