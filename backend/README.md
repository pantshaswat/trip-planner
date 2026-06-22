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

| Method | Path           | Purpose                          |
|--------|----------------|----------------------------------|
| GET    | `/api/health/` | Liveness check (added in B0)     |

(`/api/plan-trip/` arrives in milestone B3.)

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
