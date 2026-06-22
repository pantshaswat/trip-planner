// Geometry helpers for placing stop markers along the route.
// The backend gives each event a `miles_marker` (cumulative trip miles); we
// walk the route polyline by distance to find the matching [lat, lon].

const EARTH_RADIUS_MI = 3958.8;

function toRad(deg) {
  return (deg * Math.PI) / 180;
}

/** Great-circle distance between two [lat, lon] points, in miles. */
export function haversineMiles([lat1, lon1], [lat2, lon2]) {
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * EARTH_RADIUS_MI * Math.asin(Math.sqrt(a));
}

/**
 * Point on the polyline at `targetMiles` of cumulative distance.
 * Clamps to the first/last vertex outside the range.
 * @param {number[][]} geometry ordered [lat, lon] points
 */
export function pointAtMileage(geometry, targetMiles) {
  if (!geometry || geometry.length === 0) return null;
  if (targetMiles <= 0) return geometry[0];

  let acc = 0;
  for (let i = 1; i < geometry.length; i++) {
    const seg = haversineMiles(geometry[i - 1], geometry[i]);
    if (acc + seg >= targetMiles) {
      const frac = seg === 0 ? 0 : (targetMiles - acc) / seg;
      const [lat1, lon1] = geometry[i - 1];
      const [lat2, lon2] = geometry[i];
      return [lat1 + (lat2 - lat1) * frac, lon1 + (lon2 - lon1) * frac];
    }
    acc += seg;
  }
  return geometry[geometry.length - 1];
}
