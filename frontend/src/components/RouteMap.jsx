import { useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import './RouteMap.css';
import { pointAtMileage } from './map/geo';
import { MARKER_TYPES, LABEL_TO_TYPE, markerIcon, ROUTE_COLOR } from './map/markers';

// Fit the map to the whole route whenever the geometry changes.
function FitBounds({ positions }) {
  const map = useMap();
  useEffect(() => {
    if (positions.length > 1) {
      map.fitBounds(positions, { padding: [30, 30] });
    }
  }, [positions, map]);
  return null;
}

function clockFromStart(startISO, minutes) {
  const d = new Date(startISO);
  d.setMinutes(d.getMinutes() + minutes);
  return d.toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

/** Build the list of map markers from the trip result. */
function buildMarkers(result) {
  const geometry = result.route.geometry;
  const markers = [];

  // Start (current location) at the very first point.
  markers.push({
    key: 'start',
    type: 'start',
    pos: geometry[0],
    title: 'Start — current location',
    sub: result.locations.current.display_name,
  });

  // One marker per non-driving stop, placed by cumulative mileage.
  result.events.forEach((ev, i) => {
    const type = LABEL_TO_TYPE[ev.label];
    if (!type) return; // skip Driving segments
    const pos = pointAtMileage(geometry, ev.miles_marker);
    if (!pos) return;
    let sub = `${ev.miles_marker.toFixed(0)} mi · ${clockFromStart(result.start_datetime, ev.start_min)}`;
    if (type === 'pickup') sub = result.locations.pickup.display_name;
    if (type === 'dropoff') sub = result.locations.dropoff.display_name;
    markers.push({ key: `ev-${i}`, type, pos, title: ev.label, sub });
  });

  return markers;
}

export default function RouteMap({ result }) {
  const geometry = result.route.geometry;
  const markers = useMemo(() => buildMarkers(result), [result]);

  if (!geometry || geometry.length === 0) {
    return <div className="route-map-empty">No route geometry returned.</div>;
  }

  // Which marker types actually appear, for the legend.
  const presentTypes = [...new Set(markers.map((m) => m.type))];

  return (
    <div className="route-map-wrap">
      <MapContainer className="route-map" center={geometry[0]} zoom={6} scrollWheelZoom>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Polyline positions={geometry} pathOptions={{ color: ROUTE_COLOR, weight: 4 }} />
        {markers.map((m) => (
          <Marker key={m.key} position={m.pos} icon={markerIcon(m.type)}>
            <Popup>
              <strong>{m.title}</strong>
              <br />
              {m.sub}
            </Popup>
          </Marker>
        ))}
        <FitBounds positions={geometry} />
      </MapContainer>

      <ul className="map-legend">
        {presentTypes.map((t) => (
          <li key={t}>
            <span className="legend-dot" style={{ background: MARKER_TYPES[t].color }} />
            {MARKER_TYPES[t].name}
          </li>
        ))}
      </ul>
    </div>
  );
}
