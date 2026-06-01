FROM python:3.12-slim

WORKDIR /app

# Install system deps for psycopg2-binary, bcrypt, and Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[server]"

# Copy application source
COPY . .

EXPOSE 8000

# Default: start the API server
# Override with: docker compose run --rm api alembic upgrade head
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
