import { dateLocale } from "../i18n";
import type { Language } from "../i18n/types";

export interface FlightTracePoint {
  date: Date;
  altitude: number;
}

interface FlightTraceChartProps {
  points: FlightTracePoint[];
  language: Language;
  emptyLabel: string;
  ariaLabel: string;
}

const WIDTH = 640;
const HEIGHT = 180;
const PAD_LEFT = 56;
const PAD_RIGHT = 12;
const PAD_TOP = 12;
const PAD_BOTTOM = 24;

function formatTime(date: Date, language: Language): string {
  return date.toLocaleTimeString(dateLocale(language), { hour: "2-digit", minute: "2-digit" });
}

export function FlightTraceChart({ points, language, emptyLabel, ariaLabel }: FlightTraceChartProps) {
  if (points.length < 2) {
    return <p className="muted">{emptyLabel}</p>;
  }

  const altitudes = points.map((p) => p.altitude);
  const minAltitude = Math.min(...altitudes, 0);
  const maxAltitude = Math.max(...altitudes);
  const altitudeRange = maxAltitude - minAltitude || 1;

  const minTime = points[0].date.getTime();
  const maxTime = points[points.length - 1].date.getTime();
  const timeRange = maxTime - minTime || 1;

  const plotWidth = WIDTH - PAD_LEFT - PAD_RIGHT;
  const plotHeight = HEIGHT - PAD_TOP - PAD_BOTTOM;

  const xFor = (date: Date) => PAD_LEFT + ((date.getTime() - minTime) / timeRange) * plotWidth;
  const yFor = (altitude: number) =>
    PAD_TOP + plotHeight - ((altitude - minAltitude) / altitudeRange) * plotHeight;

  const linePath = points
    .map((p, i) => `${i === 0 ? "M" : "L"}${xFor(p.date).toFixed(1)},${yFor(p.altitude).toFixed(1)}`)
    .join(" ");
  const areaPath =
    `${linePath} L${xFor(points[points.length - 1].date).toFixed(1)},${(PAD_TOP + plotHeight).toFixed(1)} ` +
    `L${xFor(points[0].date).toFixed(1)},${(PAD_TOP + plotHeight).toFixed(1)} Z`;

  const midIndex = Math.floor((points.length - 1) / 2);

  return (
    <svg className="flight-trace-chart" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label={ariaLabel}>
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

      <text x={4} y={yFor(maxAltitude) + 4} fontSize={11} fill="var(--text-muted)">
        {Math.round(maxAltitude)}m
      </text>
      <text x={4} y={yFor(minAltitude) + 4} fontSize={11} fill="var(--text-muted)">
        {Math.round(minAltitude)}m
      </text>

      <text x={xFor(points[0].date)} y={HEIGHT - 4} fontSize={11} fill="var(--text-muted)">
        {formatTime(points[0].date, language)}
      </text>
      <text
        x={xFor(points[midIndex].date)}
        y={HEIGHT - 4}
        fontSize={11}
        fill="var(--text-muted)"
        textAnchor="middle"
      >
        {formatTime(points[midIndex].date, language)}
      </text>
      <text
        x={xFor(points[points.length - 1].date)}
        y={HEIGHT - 4}
        fontSize={11}
        fill="var(--text-muted)"
        textAnchor="end"
      >
        {formatTime(points[points.length - 1].date, language)}
      </text>
    </svg>
  );
}
