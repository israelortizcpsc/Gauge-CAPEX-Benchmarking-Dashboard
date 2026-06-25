# Backend image: Django + DRF served by gunicorn, static via whitenoise.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_DEBUG=False

WORKDIR /app

# Install deps first for layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Collect static (admin + DRF browsable API assets) at build time.
RUN DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput

EXPOSE 8000

# Migrate, seed if empty, then serve. Seeding on first boot makes the live
# demo self-populating; SEED_ON_START=0 disables it.
CMD ["sh", "-c", "python manage.py migrate --noinput && \
    python manage.py seed_if_empty && \
    gunicorn gauge.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3"]
