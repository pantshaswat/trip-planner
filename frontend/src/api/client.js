// Thin wrapper around the trip-planner backend.
// Base URL comes from VITE_API_BASE_URL (falls back to localhost for dev).

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * POST the 4 driver inputs to the planner.
 * Returns the parsed JSON on success; throws Error(message) on failure
 * (validation, geocoding, routing, or network).
 */
export async function planTrip(payload) {
  let resp;
  try {
    resp = await fetch(`${BASE_URL}/api/plan-trip/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  } catch {
    throw new Error('Could not reach the server. Is the backend running?');
  }

  let data = null;
  try {
    data = await resp.json();
  } catch {
    /* non-JSON body; handled below */
  }

  if (!resp.ok) {
    throw new Error(extractError(data) || `Request failed (${resp.status}).`);
  }
  return data;
}

// The backend returns either {error: "..."} or DRF field errors {field: [...]}.
function extractError(data) {
  if (!data) return null;
  if (typeof data.error === 'string') return data.error;
  const first = Object.values(data)[0];
  if (Array.isArray(first)) return first[0];
  if (typeof first === 'string') return first;
  return null;
}
