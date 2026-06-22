import LogSheet from './LogSheet';
import './LogSheet.css';

/** Renders one daily log sheet per calendar day in the trip. */
export default function LogSheets({ days }) {
  if (!days || days.length === 0) return null;
  return (
    <section className="log-sheets">
      <div className="log-sheets-head">
        <h3 className="log-sheets-title">Daily logs</h3>
        <span className="log-sheets-count">
          {days.length} {days.length === 1 ? 'day' : 'days'}
        </span>
      </div>
      {days.map((day) => (
        <LogSheet key={day.date} day={day} />
      ))}
    </section>
  );
}
