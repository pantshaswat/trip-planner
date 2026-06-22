# Backend — Trip Planner API

Django 6 + Django REST Framework. Package manager: **uv**.

## Setup

```bash
cd backend
cp .env.example .env        # then edit secrets for real deployments
uv sync                     # install deps from uv.lock into .venv
uv run python manage.py migrate
uv run python manage.py runserver
```

API base: `http://127.0.0.1:8000/api/`

## Endpoints

| Method | Path              | Purpose                                            |
|--------|-------------------|----------------------------------------------------|
| GET    | `/api/health/`    | Liveness check                                     |
| POST   | `/api/plan-trip/` | Geocode → route → HOS simulate → route + logs JSON |
| GET    | `/api/docs/`      | **Swagger UI** — try the API in the browser        |
| GET    | `/api/schema/`    | Raw OpenAPI 3 schema                               |

Open `http://127.0.0.1:8000/api/docs/`, expand **POST /api/plan-trip/**,
click *Try it out*, and send the prefilled example.

### `POST /api/plan-trip/` body

```json
{
  "current_location": "Chicago, IL",
  "pickup_location": "Joliet, IL",
  "dropoff_location": "St. Louis, MO",
  "current_cycle_used": 10,
  "start_datetime": "2026-06-22T08:00:00Z"
}
```

`start_datetime` is optional (defaults to now, UTC) and only positions events
onto calendar days for the log sheets. Response contains `locations`, `route`
(per-leg + combined `[lat,lon]` geometry), `events`, `summary`, and per-day
`days`.

## Tests

```bash
uv run python manage.py test api      # all 32 tests, offline (network mocked)
```

## Layout

```
backend/
  config/        Django project (settings, urls, wsgi/asgi)
  api/           DRF app — views, urls, and later the HOS engine + serializers
  manage.py
  .env.example   Copy to .env locally; .env is git-ignored
  pyproject.toml / uv.lock
```

## Environment variables

See `.env.example`. Read via `django-environ`.

| Var | Default | Use |
|-----|---------|-----|
| `DEBUG` | `True` | Django debug mode |
| `SECRET_KEY` | dev placeholder | Django crypto signing |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Allowed Host headers |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173` | Frontend origins allowed to call the API |
