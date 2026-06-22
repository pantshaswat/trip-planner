import { useMemo } from 'react';
import {
  ROWS, ROW_INDEX, MINUTES_PER_DAY, fillDay, rowTotals, hoursMinutes,
} from './log/logGeometry';

// SVG geometry (user units; scaled responsively via viewBox).
const LEFT = 132;     // left labels column
const GRID_W = 696;   // 24h timeline width  (29 px / hour)
const RIGHT = 64;     // hour-totals column
const TOP = 26;       // hour numbers above grid
const ROW_H = 32;
const GRID_H = ROW_H * ROWS.length;
const REMARK_H = 92;
const W = LEFT + GRID_W + RIGHT;
const H = TOP + GRID_H + REMARK_H;

const x = (min) => LEFT + (min / MINUTES_PER_DAY) * GRID_W;
const rowCenterY = (status) => TOP + ROW_INDEX[status] * ROW_H + ROW_H / 2;

function hourLabel(h) {
  if (h === 0 || h === 24) return 'Mid';
  if (h === 12) return 'Noon';
  return String(h % 12 === 0 ? 12 : h % 12);
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
      else d += `L ${x1} ${y} `; // vertical/diagonal connector to this row
      d += `L ${x2} ${y} `;       // horizontal run across this segment
    });
    return d;
  }, [filled]);

  // Remarks: only real (labelled) transitions.
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
        {/* Hour numbers + vertical hour/quarter gridlines */}
        {Array.from({ length: 25 }, (_, h) => (
          <g key={h}>
            <text x={x(h * 60)} y={TOP - 10} className="log-hour" textAnchor="middle">
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

        {/* Row bands, labels, separators, and per-row totals */}
        {ROWS.map((row, i) => {
          const yTop = TOP + i * ROW_H;
          return (
            <g key={row.key}>
              <rect x={LEFT} y={yTop} width={GRID_W} height={ROW_H}
                    className={i % 2 ? 'log-band-alt' : 'log-band'} />
              <text x={LEFT - 10} y={yTop + ROW_H / 2} className="log-row-label"
                    textAnchor="end" dominantBaseline="middle">
                {i + 1}. {row.label}
              </text>
              <text x={LEFT + GRID_W + RIGHT / 2} y={yTop + ROW_H / 2}
                    className="log-row-total" textAnchor="middle" dominantBaseline="middle">
                {hoursMinutes(totals[row.key])}
              </text>
            </g>
          );
        })}

        {/* Grid outline */}
        <rect x={LEFT} y={TOP} width={GRID_W} height={GRID_H} className="log-grid-outline" />

        {/* The duty-status line */}
        <path d={linePath} className="log-line" />

        {/* Remarks: tick + rotated label at each labelled transition */}
        {remarks.map((seg, i) => (
          <g key={i} transform={`translate(${x(seg.start_min)}, ${TOP + GRID_H})`}>
            <line x1="0" y1="0" x2="0" y2="10" className="log-remark-tick" />
            <text x="0" y="14" className="log-remark"
                  transform="rotate(60)" dominantBaseline="middle">
              {seg.label}
            </text>
          </g>
        ))}
      </svg>
    </figure>
  );
}
