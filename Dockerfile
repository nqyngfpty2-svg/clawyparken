# clawyparken – Docker image
# Runs FastAPI via uvicorn on port 18880.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (small set; add build-essential only if you add compiled deps)
RUN apt-get update -y \
  && apt-get install -y --no-install-recommends ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Install python deps first (better layer cache)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -U pip wheel \
  && pip install --no-cache-dir -r /app/requirements.txt

# Copy app
COPY parking_app /app/parking_app

# Create runtime dirs (will typically be bind-mounted/volumes in prod)
RUN mkdir -p /app/parking_app/data /app/parking_app/secrets /app/parking_app/plan /app/parking_app/static

EXPOSE 18880

# Run migrations on start, then serve.
CMD ["bash", "-lc", "python -c 'from parking_app.app.db import migrate; migrate(); print(\"migrate ok\")' && uvicorn parking_app.app.main:app --host 0.0.0.0 --port 18880"]
