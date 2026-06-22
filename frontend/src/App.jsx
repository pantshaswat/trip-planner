import { useState } from 'react';
import './App.css';
import TripForm from './components/TripForm';
import { planTrip } from './api/client';

export default function App() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  async function handlePlan(payload) {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await planTrip(payload);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header-inner">
          <div className="brand">
            <span className="brand-mark" aria-hidden="true">▰</span>
            <span className="brand-name">TripLogger</span>
          </div>
          <span className="brand-tagline">HOS-compliant trip &amp; ELD log planner</span>
        </div>
      </header>

      <main className="app-main">
        <section className="panel form-panel">
          <h1 className="panel-title">Plan a trip</h1>
          <p className="panel-sub">
            Enter your route and current cycle. We apply federal Hours-of-Service
            rules and generate your daily logs.
          </p>
          <TripForm onSubmit={handlePlan} loading={loading} />
          {error && <div className="alert alert-error" role="alert">{error}</div>}
        </section>

        <section className="panel output-panel">
          {result ? (
            <div className="result-stub">
              <h2 className="panel-title">Trip planned</h2>
              <ul className="result-facts">
                <li>
                  <span>Total distance</span>
                  <strong>{result.route.total_distance_miles.toFixed(0)} mi</strong>
                </li>
                <li>
                  <span>Driving time</span>
                  <strong>{(result.summary.driving_minutes / 60).toFixed(1)} h</strong>
                </li>
                <li>
                  <span>Duty events</span>
                  <strong>{result.events.length}</strong>
                </li>
                <li>
                  <span>Log days</span>
                  <strong>{result.days.length}</strong>
                </li>
              </ul>
              <p className="placeholder-note">
                Map and daily log sheets render here next (milestones F1–F2).
              </p>
            </div>
          ) : (
            <div className="empty-state">
              <span className="empty-mark" aria-hidden="true">▰▰▰</span>
              <p>Your route map and daily logs will appear here.</p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
