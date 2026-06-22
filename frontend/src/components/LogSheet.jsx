import { useMemo } from 'react';
import {
  ROWS, ROW_INDEX, MINUTES_PER_DAY, fillDay, rowTotals, hoursMinutes,
} from './log/logGeometry';

// SVG geometry (user units; scaled responsively via viewBox).
const LEFT = 132;     // left labels column
const GRID_W = 696;   // 24h timeline width  (29 px / hour)
const RIGHT = 84;     // hours + minutes totals columns
const TOP = 30;       // hour numbers above grid
const ROW_H = 32;
const GRID_H = ROW_H * ROWS.length;
const REMARK_H = 112;
const W = LEFT + GRID_W + RIGHT;
const H = TOP + GRID_H + REMARK_H;

const HRS_X = LEFT + GRID_W + 28;
const MIN_X = LEFT + GRID_W + 62;

const x = (min) => LEFT + (min / MINUTES_PER_DAY) * GRID_W;
const rowCenterY = (status) => TOP + ROW_INDEX[status] * ROW_H + ROW_H / 2;

function hourLabel(h) {
  if (h === 0 || h === 24) return 'Mid';
  if (h === 12) return 'Noon';
  return String(h % 12 === 0 ? 12 : h % 12);
}

// Split minutes into whole hours + minutes rounded to 00/15/30/45 (paper-log style).
function splitHM(total) {
  let hh = Math.floor(total / 60);
  let mm = Math.round((total - hh * 60) / 15) * 15;
  if (mm === 60) { hh += 1; mm = 0; }
  return { hh, mm: String(mm).padStart(2, '0') };
}

export default function LogSheet({ day }) {
  const filled = useMemo(() => fillDay(day.segments), [day]);
  const totals = useMemo(() => rowTotals(filled), [filled]);

  // The continuous status line: horizontal run per segment + vertical connector
  // between segments that change rows.
  const linePath = useMemo(() => {
    let d = '';
    filled.forEach((seg, i) => {
      const y = rowCenterY(seg.duty_status);
      const x1 = x(seg.start_min);
      const x2 = x(seg.end_min);
      if (i === 0) d += `M ${x1} ${y} `;
      else d += `L ${x1} ${y} `; // vertical connector to this row
      d += `L ${x2} ${y} `;       // horizontal run across this segment
    });
    return d;
  }, [filled]);

  // Remarks: every real (labelled) status change.
  const remarks = filled.filter((s) => s.label);

  const dateLabel = new Date(`${day.date}T00:00:00`).toLocaleDateString(undefined, {
    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
  });

  return (
    <figure className="log-sheet">
      <figcaption className="log-sheet-head">
        <span className="log-date">{dateLabel}</span>
        <span className="log-grand-total">
          Total {hoursMinutes(Object.values(totals).reduce((a, b) => a + b, 0))}
        </span>
      </figcaption>

      <svg className="log-svg" viewBox={`0 0 ${W} ${H}`} role="img"
           aria-label={`Daily log for ${day.date}`}>
        {/* Totals column headers */}
        <text x={HRS_X} y={TOP - 12} className="log-total-head" textAnchor="middle">Hrs</text>
        <text x={MIN_X} y={TOP - 12} className="log-total-head" textAnchor="middle">Min</text>

        {/* Hour numbers + vertical hour gridlines */}
        {Array.from({ length: 25 }, (_, h) => (
          <g key={h}>
            <text x={x(h * 60)} y={TOP - 12} className="log-hour" textAnchor="middle">
              {hourLabel(h)}
            </text>
            <line x1={x(h * 60)} y1={TOP} x2={x(h * 60)} y2={TOP + GRID_H}
                  className="log-grid-hour" />
          </g>
        ))}
        {/* Quarter-hour minor ticks */}
        {Array.from({ length: 24 * 4 + 1 }, (_, q) => (
          q % 4 !== 0 ? (
            <line key={`q${q}`} x1={x(q * 15)} y1={TOP} x2={x(q * 15)} y2={TOP + GRID_H}
                  className="log-grid-quarter" />
          ) : null
        ))}

        {/* Row bands, labels, and per-row hour/minute totals */}
        {ROWS.map((row, i) => {
          const yTop = TOP + i * ROW_H;
          const yMid = yTop + ROW_H / 2;
          const { hh, mm } = splitHM(totals[row.key]);
          return (
            <g key={row.key}>
              <rect x={LEFT} y={yTop} width={GRID_W} height={ROW_H}
                    className={i % 2 ? 'log-band-alt' : 'log-band'} />
              <text x={LEFT - 10} y={yMid} className="log-row-label"
                    textAnchor="end" dominantBaseline="middle">
                {i + 1}. {row.label}
              </text>
              <text x={HRS_X} y={yMid} className="log-total-num"
                    textAnchor="middle" dominantBaseline="middle">{hh}</text>
              <text x={MIN_X} y={yMid} className="log-total-num"
                    textAnchor="middle" dominantBaseline="middle">{mm}</text>
            </g>
          );
        })}

        {/* Separator between hours and minutes columns */}
        <line x1={(HRS_X + MIN_X) / 2} y1={TOP} x2={(HRS_X + MIN_X) / 2} y2={TOP + GRID_H}
              className="log-grid-hour" />

        {/* Grid outline */}
        <rect x={LEFT} y={TOP} width={GRID_W} height={GRID_H} className="log-grid-outline" />

        {/* The duty-status line */}
        <path d={linePath} className="log-line" />

        {/* Flags (45deg marks) at each status change, on the timeline */}
        {remarks.map((seg, i) => {
          const fx = x(seg.start_min);
          const fy = rowCenterY(seg.duty_status);
          return (
            <line key={`flag-${i}`} x1={fx} y1={fy} x2={fx + 8} y2={fy - 8}
                  className="log-flag" />
          );
        })}

        {/* Remarks: drop line + angled "City, ST" / activity under the grid */}
        {remarks.map((seg, i) => (
          <g key={`rem-${i}`} transform={`translate(${x(seg.start_min)}, ${TOP + GRID_H})`}>
            <line x1="0" y1="0" x2="0" y2="9" className="log-remark-tick" />
            <g transform="rotate(58)">
              <text className="log-remark" x="12" y="0">
                <tspan x="12" dy="0" className="log-remark-loc">{seg.location || '—'}</tspan>
                <tspan x="12" dy="9">{seg.activity}</tspan>
              </text>
            </g>
          </g>
        ))}
      </svg>
    </figure>
  );
}
