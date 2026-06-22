// Marker styling + how engine event labels map to map markers.
import L from 'leaflet';

// Brand orange for the route line. (Leaflet writes an SVG stroke attribute,
// which can't read a CSS variable, so the value lives here in config.)
export const ROUTE_COLOR = '#F85F14';

// type -> { color, glyph, name }. Colors stay near the brand; a couple of
// distinct hues (fuel, break) aid quick scanning.
export const MARKER_TYPES = {
  start: { color: '#1A1A1A', glyph: 'A', name: 'Start' },
  pickup: { color: '#F85F14', glyph: 'P', name: 'Pickup' },
  dropoff: { color: '#D44E0D', glyph: 'D', name: 'Dropoff' },
  fuel: { color: '#2D7DD2', glyph: 'F', name: 'Fuel stop' },
  break: { color: '#E8A33D', glyph: 'B', name: '30-min break' },
  rest: { color: '#5A6872', glyph: 'R', name: '10-hr rest' },
  restart: { color: '#7A4FB5', glyph: 'C', name: '34-hr restart' },
};

// Engine event label -> marker type.
export const LABEL_TO_TYPE = {
  Pickup: 'pickup',
  Dropoff: 'dropoff',
  'Fuel stop': 'fuel',
  '30-min break': 'break',
  '10-hr rest': 'rest',
  '34-hr restart': 'restart',
};

const iconCache = {};

/** A circular CSS divIcon — avoids Leaflet's broken default image paths. */
export function markerIcon(type) {
  if (iconCache[type]) return iconCache[type];
  const { color, glyph } = MARKER_TYPES[type] || MARKER_TYPES.start;
  const icon = L.divIcon({
    className: 'route-pin',
    html: `<span class="route-pin-dot" style="background:${color}">${glyph}</span>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -12],
  });
  iconCache[type] = icon;
  return icon;
}
