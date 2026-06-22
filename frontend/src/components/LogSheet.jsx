import { useMemo } from 'react';
import {
  ROWS, ROW_INDEX, MINUTES_PER_DAY, fillDay, rowTotals,
} from './log/logGeometry';

const AVG_SPEED_MPH = 55; // backend assumption; used only to show miles/day

// SVG geometry (user units; scaled responsively via viewBox).
const LEFT = 150;
const GRID_W = 696;   // 24h timeline width  (29 px / hour)
const RIGHT = 84;     // hours + minutes totals columns
const TOP = 34;       // top hour numbers above grid
const ROW_H = 30;
const GRID_H = ROW_H * ROWS.length;
const GRID_BOTTOM = TOP + GRID_H;
const STRIP_BOT = GRID_BOTTOM + 8;       // bottom tick strip depth
const BOTTOM_NUM_Y = GRID_BOTTOM + 18;   // bottom hour numbers
const REMARK_TOP = GRID_BOTTOM + 30;     // brackets sit here, below the strip
const BRACKET_DROP = 7;
const REMARK_H = 168;
const W = LEFT + GRID_W + RIGHT;
const H = GRID_BOTTOM + REMARK_H;

// Remark leader: a straight line dropping down-and-left at this angle, with the
// two text lines riding along it (the line reads like an underline).
const LEADER_DEG = 52;
const LEADER_COS = Math.cos((LEADER_DEG * Math.PI) / 180);
const LEADER_SIN = Math.sin((LEADER_DEG * Math.PI) / 180);

const HRS_X = LEFT + GRID_W + 28;
const MIN_X = LEFT + GRID_W + 62;

const x = (min) => LEFT + (min / MINUTES_PER_DAY) * GRID_W;
const rowCenterY = (status) => TOP + ROW_INDEX[status] * ROW_H + ROW_H / 2;

function hourLabel(h) {
  if (h === 0 || h === 24) return 'Mid';
  if (h === 12) return 'Noon';
  return String(h % 12 === 0 ? 12 : h % 12);
}

function splitHM(total) {
  let hh = Math.floor(total / 60);
  let mm = Math.round((total - hh * 60) / 15) * 15;
  if (mm === 60) { hh += 1; mm = 0; }
  return { hh, mm: String(mm).padStart(2, '0') };
}

function Field({ label, value, wide }) {
  return (
    <div className={`log-field ${wide ? 'wide' : ''}`}>
      <span className="log-field-value">{value || ' '}</span>
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

  // Remark per real stop. Plain "Driving" resumes are skipped so the labels
  // don't pile up at close-together changes (matches the paper logs).
  const remarks = filled.filter((s) => s.label && s.activity !== 'Driving');
  const brackets = filled.filter((s) => s.label && s.duty_status !== 'Driving');

  const drivingMiles = Math.round((totals.Driving / 60) * AVG_SPEED_MPH);
  const dateLabel = new Date(`${day.date}T00:00:00`).toLocaleDateString(undefined, {
    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
  });

  return (
    <figure className="log-sheet">
      <div className="log-band-top">
        <div className="log-band-left">
          <span className="log-sheet-title">Driver's Daily Log</span>
          <span className="log-sheet-date">{dateLabel}</span>
        </div>
        <div className="log-fields">
          <Field label="Total miles driving today" value={`${drivingMiles}`} />
          <Field label="Total truck mileage today" value={`${drivingMiles}`} />
          <Field label="Carrier" value="—" wide />
          <Field label="Home terminal" value="—" wide />
          <Field label="Co-driver" value="N/A" />
        </div>
      </div>

      <svg className="log-svg" viewBox={`0 0 ${W} ${H}`} role="img"
           aria-label={`Daily log for ${day.date}`}>
        {/* Totals column headers */}
        <text x={HRS_X} y={TOP - 14} className="log-total-head" textAnchor="middle">Hrs</text>
        <text x={MIN_X} y={TOP - 14} className="log-total-head" textAnchor="middle">Min</text>

        {/* 1) Row bands (drawn first so grid lines sit on top), labels, totals */}
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

        {/* 2) Full-height hour lines spanning all four rows */}
        {Array.from({ length: 25 }, (_, h) => (
          <line key={`hl${h}`} x1={x(h * 60)} y1={TOP} x2={x(h * 60)} y2={GRID_BOTTOM}
                className="log-grid-hour" />
        ))}

        {/* 3) Per-row 15-min ticks: each hour split into four inside EVERY row,
              hanging from that row's top edge (:30 taller than :15/:45), plus a
              matching set rising from the bottom edge of the bottom row. */}
        {ROWS.map((row, i) => {
          const yTop = TOP + i * ROW_H;
          const isLast = i === ROWS.length - 1;
          return (
            <g key={`ticks-${i}`} className="log-minor-tick">
              {Array.from({ length: 24 * 4 + 1 }, (_, q) => {
                if (q % 4 === 0) return null;          // hour line handled above
                const len = q % 2 === 0 ? 9 : 5;        // :30 taller than :15/:45
                const tx = x(q * 15);
                return (
                  <g key={q}>
                    <line x1={tx} y1={yTop} x2={tx} y2={yTop + len} />
                    {isLast && <line x1={tx} y1={GRID_BOTTOM} x2={tx} y2={GRID_BOTTOM - len} />}
                  </g>
                );
              })}
            </g>
          );
        })}

        {/* Hour numbers, top + bottom scales */}
        {Array.from({ length: 25 }, (_, h) => (
          <g key={`hn${h}`}>
            <text x={x(h * 60)} y={TOP - 14} className="log-hour" textAnchor="middle">{hourLabel(h)}</text>
            <text x={x(h * 60)} y={BOTTOM_NUM_Y} className="log-hour" textAnchor="middle">{hourLabel(h)}</text>
          </g>
        ))}

        {/* 4) Bottom tick strip below the grid: hour ticks + half-hour ticks */}
        <g className="log-strip">
          {Array.from({ length: 25 }, (_, h) => (
            <line key={`sh${h}`} x1={x(h * 60)} y1={GRID_BOTTOM} x2={x(h * 60)} y2={STRIP_BOT}
                  className="log-strip-hour" />
          ))}
          {Array.from({ length: 24 }, (_, h) => (
            <line key={`s30-${h}`} x1={x(h * 60 + 30)} y1={GRID_BOTTOM} x2={x(h * 60 + 30)} y2={STRIP_BOT - 3}
                  className="log-strip-half" />
          ))}
        </g>

        <line x1={(HRS_X + MIN_X) / 2} y1={TOP} x2={(HRS_X + MIN_X) / 2} y2={GRID_BOTTOM}
              className="log-grid-hour" />
        <rect x={LEFT} y={TOP} width={GRID_W} height={GRID_H} className="log-grid-outline" />

        {/* REMARKS label at the bottom-left, where the leaders begin */}
        <text x="6" y={REMARK_TOP + 12} className="log-remarks-label">REMARKS</text>

        {/* U-brackets (cups): stationary, non-driving durations only */}
        {brackets.map((s, i) => {
          const x1 = x(s.start_min);
          const x2 = x(s.end_min);
          const yb = REMARK_TOP + BRACKET_DROP;
          return (
            <path key={`br-${i}`}
                  d={`M ${x1} ${REMARK_TOP} L ${x1} ${yb} L ${x2} ${yb} L ${x2} ${REMARK_TOP}`}
                  className="log-bracket" />
          );
        })}

        {/* Duty-status line (black) + red corner dots */}
        <path d={linePath} className="log-line" />
        {cornerDots.map(([cx, cy], i) => (
          <circle key={`dot-${i}`} cx={cx} cy={cy} r="2.4" className="log-corner-dot" />
        ))}

        {/* Flags: short 45deg ticks on the grid at each status change */}
        {cornerDots.filter((_, i) => i % 2 === 0).map(([cx], i) => {
          // one flag per change, centered on the connector's midpoint
          const [, y1] = cornerDots[i * 2];
          const [, y2] = cornerDots[i * 2 + 1];
          const ym = (y1 + y2) / 2;
          return (
            <line key={`flag-${i}`} x1={cx - 4} y1={ym + 4} x2={cx + 4} y2={ym - 4}
                  className="log-flag" />
          );
        })}

        {/* Remarks: a single 52deg leader from the bracket region with the two
            text lines ("City, ST" / activity) riding along it as an underline. */}
        {remarks.map((s, i) => {
          const rx = x(s.start_min);
          const py = REMARK_TOP + BRACKET_DROP;          // start at bracket bottom
          const loc = s.location || '—';
          const act = s.activity || '';
          const w = Math.min(132, Math.max(46, Math.max(loc.length, act.length) * 4.2));
          const qx = rx - LEADER_COS * w;                 // far (down-left) end
          const qy = py + LEADER_SIN * w;
          return (
            <g key={`rem-${i}`} transform={`translate(${qx}, ${qy}) rotate(-${LEADER_DEG})`}>
              <line x1="0" y1="0" x2={w} y2="0" className="log-leader" />
              <text className="log-remark" textAnchor="start">
                <tspan x="2" y="-13" className="log-remark-loc">{loc}</tspan>
                <tspan x="2" y="-3.5">{act}</tspan>
              </text>
            </g>
          );
        })}
      </svg>

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
