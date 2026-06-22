import { useMemo } from 'react';
import {
  ROWS, ROW_INDEX, MINUTES_PER_DAY, fillDay, rowTotals,
} from './log/logGeometry';

const AVG_SPEED_MPH = 55; // backend assumption; used only to show miles/day

// SVG geometry (user units; scaled responsively via viewBox).
const LEFT = 132;
const GRID_W = 696;   // 24h timeline width  (29 px / hour)
const RIGHT = 84;     // hours + minutes totals columns
const TOP = 30;
const ROW_H = 32;
const GRID_H = ROW_H * ROWS.length;
const GRID_BOTTOM = TOP + GRID_H;
const REMARK_H = 120;
const W = LEFT + GRID_W + RIGHT;
const H = GRID_BOTTOM + REMARK_H;

const HRS_X = LEFT + GRID_W + 28;
const MIN_X = LEFT + GRID_W + 62;
const BRACKET_DROP = 7; // how far the U hangs below the grid

const x = (min) => LEFT + (min / MINUTES_PER_DAY) * GRID_W;
const rowCenterY = (status) => TOP + ROW_INDEX[status] * ROW_H + ROW_H / 2;

function hourLabel(h) {
  if (h === 0 || h === 24) return 'Mid';
  if (h === 12) return 'Noon';
  return String(h % 12 === 0 ? 12 : h % 12);
}

// Split minutes into whole hours + minutes rounded to 00/15/30/45.
function splitHM(total) {
  let hh = Math.floor(total / 60);
  let mm = Math.round((total - hh * 60) / 15) * 15;
  if (mm === 60) { hh += 1; mm = 0; }
  return { hh, mm: String(mm).padStart(2, '0') };
}

// A small labelled field for the header/footer bands.
function Field({ label, value, wide }) {
  return (
    <div className={`log-field ${wide ? 'wide' : ''}`}>
      <span className="log-field-value">{value || ' '}</span>
      <span className="log-field-label">{label}</span>
    </div>
  );
}

export default function LogSheet({ day }) {
  const filled = useMemo(() => fillDay(day.segments), [day]);
  const totals = useMemo(() => rowTotals(filled), [filled]);

  const linePath = useMemo(() => {
    let d = '';
    filled.forEach((seg, i) => {
      const y = rowCenterY(seg.duty_status);
      const x1 = x(seg.start_min);
      const x2 = x(seg.end_min);
      d += i === 0 ? `M ${x1} ${y} ` : `L ${x1} ${y} `;
      d += `L ${x2} ${y} `;
    });
    return d;
  }, [filled]);

  // Corner dots: where the line steps between rows.
  const cornerDots = useMemo(() => {
    const dots = [];
    for (let i = 1; i < filled.length; i++) {
      const yPrev = rowCenterY(filled[i - 1].duty_status);
      const yCur = rowCenterY(filled[i].duty_status);
      if (yPrev !== yCur) {
        const cx = x(filled[i].start_min);
        dots.push([cx, yPrev], [cx, yCur]);
      }
    }
    return dots;
  }, [filled]);

  const remarks = filled.filter((s) => s.label);
  // Brackets mark the durations the truck was NOT moving (non-driving stops).
  const brackets = remarks.filter((s) => s.duty_status !== 'Driving');

  const drivingMiles = Math.round((totals.Driving / 60) * AVG_SPEED_MPH);
  const dateLabel = new Date(`${day.date}T00:00:00`).toLocaleDateString(undefined, {
    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
  });

  return (
    <figure className="log-sheet">
      {/* Header band */}
      <div className="log-band-top">
        <div className="log-band-left">
          <span className="log-sheet-title">Driver's Daily Log</span>
          <span className="log-sheet-date">{dateLabel}</span>
        </div>
        <div className="log-fields">
          <Field label="Total miles driving today" value={`${drivingMiles}`} />
          <Field label="Carrier" value="—" wide />
          <Field label="Home terminal" value="—" wide />
          <Field label="Co-driver" value="N/A" />
        </div>
      </div>

      <svg className="log-svg" viewBox={`0 0 ${W} ${H}`} role="img"
           aria-label={`Daily log for ${day.date}`}>
        <text x={HRS_X} y={TOP - 12} className="log-total-head" textAnchor="middle">Hrs</text>
        <text x={MIN_X} y={TOP - 12} className="log-total-head" textAnchor="middle">Min</text>

        {/* Hour numbers + vertical hour gridlines */}
        {Array.from({ length: 25 }, (_, h) => (
          <g key={h}>
            <text x={x(h * 60)} y={TOP - 12} className="log-hour" textAnchor="middle">
              {hourLabel(h)}
            </text>
            <line x1={x(h * 60)} y1={TOP} x2={x(h * 60)} y2={GRID_BOTTOM} className="log-grid-hour" />
          </g>
        ))}
        {/* Quarter-hour minor ticks */}
        {Array.from({ length: 24 * 4 + 1 }, (_, q) => (
          q % 4 !== 0 ? (
            <line key={`q${q}`} x1={x(q * 15)} y1={TOP} x2={x(q * 15)} y2={GRID_BOTTOM}
                  className="log-grid-quarter" />
          ) : null
        ))}

        {/* Row bands, labels, totals */}
        {ROWS.map((row, i) => {
          const yTop = TOP + i * ROW_H;
          const yMid = yTop + ROW_H / 2;
          const { hh, mm } = splitHM(totals[row.key]);
          return (
            <g key={row.key}>
              <rect x={LEFT} y={yTop} width={GRID_W} height={ROW_H}
                    className={i % 2 ? 'log-band-alt' : 'log-band'} />
              <text x={LEFT - 10} y={yMid} className="log-row-label"
                    textAnchor="end" dominantBaseline="middle">{i + 1}. {row.label}</text>
              <text x={HRS_X} y={yMid} className="log-total-num"
                    textAnchor="middle" dominantBaseline="middle">{hh}</text>
              <text x={MIN_X} y={yMid} className="log-total-num"
                    textAnchor="middle" dominantBaseline="middle">{mm}</text>
            </g>
          );
        })}

        <line x1={(HRS_X + MIN_X) / 2} y1={TOP} x2={(HRS_X + MIN_X) / 2} y2={GRID_BOTTOM}
              className="log-grid-hour" />
        <rect x={LEFT} y={TOP} width={GRID_W} height={GRID_H} className="log-grid-outline" />

        {/* U-brackets: truck stationary (non-driving) durations */}
        {brackets.map((s, i) => {
          const x1 = x(s.start_min);
          const x2 = x(s.end_min);
          const yb = GRID_BOTTOM + BRACKET_DROP;
          return (
            <path key={`br-${i}`}
                  d={`M ${x1} ${GRID_BOTTOM} L ${x1} ${yb} L ${x2} ${yb} L ${x2} ${GRID_BOTTOM}`}
                  className="log-bracket" />
          );
        })}

        {/* The duty-status line + corner dots */}
        <path d={linePath} className="log-line" />
        {cornerDots.map(([cx, cy], i) => (
          <circle key={`dot-${i}`} cx={cx} cy={cy} r="2.4" className="log-corner-dot" />
        ))}

        {/* Remarks: drop line + 45deg-left "City, ST" / activity */}
        {remarks.map((s, i) => {
          const rx = x(s.start_min);
          return (
            <g key={`rem-${i}`}>
              <line x1={rx} y1={GRID_BOTTOM + BRACKET_DROP} x2={rx} y2={GRID_BOTTOM + 20}
                    className="log-remark-tick" />
              <g transform={`translate(${rx}, ${GRID_BOTTOM + 22}) rotate(-45)`}>
                <text className="log-remark" textAnchor="end">
                  <tspan x="0" dy="0" className="log-remark-loc">{s.location || '—'}</tspan>
                  <tspan x="0" dy="9">{s.activity}</tspan>
                </text>
              </g>
            </g>
          );
        })}
      </svg>

      {/* Footer band */}
      <div className="log-band-bottom">
        <Field label="Shipper" value="—" wide />
        <Field label="Commodity" value="—" wide />
        <Field label="Load / Pro No." value="—" />
        <div className="log-signature">
          <span className="log-field-value log-sign-line" />
          <span className="log-field-label">Driver signature</span>
        </div>
      </div>
    </figure>
  );
}
