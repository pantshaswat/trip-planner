// Typeahead place search via Photon (komoot) — free, key-less.
// Used only for autocomplete suggestions; the backend still does the
// authoritative geocode (Nominatim) + routing (OSRM) on submit.

const PHOTON_URL = import.meta.env.VITE_PHOTON_URL || 'https://photon.komoot.io/api';

/** Build a readable one-line label from a Photon feature's properties. */
function formatLabel(p) {
  const primary =
    p.name ||
    [p.street, p.housenumber].filter(Boolean).join(' ') ||
    p.city ||
    p.county;
  const rest = [
    p.city && p.city !== primary ? p.city : null,
    p.state,
    p.country,
  ].filter(Boolean);
  return [primary, ...rest].filter(Boolean).join(', ');
}

/**
 * Search places matching `query`. Returns up to `limit` {id, label} items.
 * Pass an AbortSignal so stale in-flight requests can be cancelled.
 * Returns [] on any error (typeahead must never block typing).
 */
export async function searchPlaces(query, { signal, limit = 5 } = {}) {
  const q = query.trim();
  if (q.length < 3) return [];

  const url = `${PHOTON_URL}?q=${encodeURIComponent(q)}&limit=${limit}`;
  let resp;
  try {
    resp = await fetch(url, { signal });
  } catch {
    return []; // network error or aborted
  }
  if (!resp.ok) return [];

  let data;
  try {
    data = await resp.json();
  } catch {
    return [];
  }

  const seen = new Set();
  const out = [];
  for (const f of data.features || []) {
    const label = formatLabel(f.properties || {});
    if (!label || seen.has(label)) continue;
    seen.add(label);
    const props = f.properties || {};
    out.push({ id: `${props.osm_type || ''}${props.osm_id || ''}-${out.length}`, label });
  }
  return out;
}
