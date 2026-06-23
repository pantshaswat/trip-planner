# Trip Planner backend — Django + Gunicorn, built with uv.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Faster, cleaner Python in containers.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install deps first (cached layer) using only the lock + manifest.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy the app and finish the install.
COPY . .
RUN uv sync --frozen --no-dev

# Collect static assets (DRF/Swagger UI). Uses a throwaway SECRET_KEY so the
# build never depends on the real one; runtime .env supplies the real value.
RUN SECRET_KEY=build-only DEBUG=False uv run python manage.py collectstatic --noinput

EXPOSE 8000

# Run migrations then start Gunicorn. Reads /app/.env at runtime via django-environ.
CMD ["sh", "-c", "uv run python manage.py migrate --noinput && uv run gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3"]
