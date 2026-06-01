FROM python:3.12-slim

WORKDIR /app

# System deps: libpq for psycopg2, curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (includes ingestion extras for the worker)
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[ingestion]"

# Copy application source
COPY . .

EXPOSE 8000

# Default: start the API server
# Override with: docker compose run --rm api alembic upgrade head
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
