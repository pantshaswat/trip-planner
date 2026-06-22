# Trip Planner + ELD Log Generator

Trip planner and automatic ELD (Electronic Logging Device) log generator for U.S. truck
drivers. A driver enters current location, pickup, dropoff, and hours already used in their
70hr/8day cycle. The app plans the whole trip in advance — applying federal Hours-of-Service
(HOS) rules — and returns a route map (rest/break/fuel stops) plus filled-in daily log sheets.

The core is a framework-free **simulation engine** that turns the trip into an ordered list of
timed duty events. The map and log sheets just display that list.

## Monorepo layout

```
trip-planner/
  backend/    Django 6 + DRF API and the HOS engine (uv-managed)
  frontend/   React 19 + Vite shell (Leaflet map + SVG log sheets later)
  README.md
```

## Stack

| Part      | Tech |
|-----------|------|
| Backend   | Python 3.13, Django 6.0, Django REST Framework 3.17, uv |
| Frontend  | React 19, Vite 8 |
| Maps/Geo  | OpenRouteService / OSRM (routing), Nominatim (geocoding) — added in B2 |
| Hosting   | Frontend → Vercel; Backend → Render/Railway/VM |

## Run locally

**Backend** (`http://127.0.0.1:8000`):

```bash
cd backend
cp .env.example .env
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

**Frontend** (`http://localhost:5173`):

```bash
cd frontend
npm install
npm run dev
```

Health check: `curl http://127.0.0.1:8000/api/health/` → `{"status":"ok",...}`

See `backend/README.md` for API and env-var details.

## Build order (milestones)

Backend first: B0 scaffold → B1 HOS engine → B2 geocode/routing → B3 API endpoint.
Then frontend: F0 shell/design → F1 map → F2 log sheets → F3 polish. Then D0 deploy.
