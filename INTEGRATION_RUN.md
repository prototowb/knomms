# Integration Run Guide

First-time run checklist — verified against the codebase as of commit e78f691+.
All five static bugs that would have killed the first run have been fixed.
Run through this in order.

---

## Prerequisites

- Docker Compose v2.20+
- Machine with at least 16GB RAM and 50GB free disk (see `docs/05-platform-architecture.md`)
- Ollama models require ~5GB disk: `mistral:7b-instruct` + `nomic-embed-text`

---

## Step 1 — Environment

```bash
cp .env.example .env
```

Edit `.env` and set the three required secrets:

```
POSTGRES_PASSWORD=<strong-password>
MINIO_ROOT_PASSWORD=<strong-password>
SECRET_KEY=<at-least-32-random-chars>
```

Generate `SECRET_KEY`:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## Step 2 — Start data services

```bash
docker compose up -d db redis minio
```

Wait for all three to be healthy:
```bash
docker compose ps   # all three should show "healthy"
```

---

## Step 3 — Run migrations

```bash
docker compose run --rm api alembic upgrade head
```

Expected output: 5 migrations applied (`001` → `005`). If it fails:
- **`CREATE EXTENSION IF NOT EXISTS vector` fails** — confirm you are using the `pgvector/pgvector:pg16` image (not plain postgres). The image tag is in `docker-compose.yml`.
- **`DATABASE_SYNC_URL` not set** — the env is passed by docker-compose; confirm the `api` service environment block in `docker-compose.yml` is correct.

---

## Step 4 — Pull Ollama models

```bash
docker compose up -d ollama
# Wait ~60s for Ollama to start (see start_period in healthcheck)
docker compose run --rm ollama-init
```

This pulls `mistral:7b-instruct` (~4GB) and `nomic-embed-text` (~300MB). Only needed on first run; models are cached in the `ollama_models` volume.

On CPU-only hardware, change `OLLAMA_MODEL=phi3:mini-instruct-q4_K_M` in `.env` (faster inference, lower quality).

---

## Step 5 — Start everything

```bash
docker compose up -d
```

Verify:
```bash
docker compose ps          # all services running
curl http://localhost/health  # should return {"status":"ok","version":"0.1.0"}
```

---

## Step 6 — Smoke tests

### 6.1 Register + login

```bash
curl -s -X POST http://localhost/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","handle":"testuser","display_name":"Test User","password":"password123"}' \
  | python3 -m json.tool

# Save the token
TOKEN=$(curl -s -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "Token: $TOKEN"
```

### 6.2 Ingest a URL

```bash
curl -s -X POST http://localhost/api/v1/sources/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://en.wikipedia.org/wiki/Retrieval-augmented_generation"}' \
  | python3 -m json.tool
```

Note the `id` from the response. Watch the worker logs:
```bash
docker compose logs -f worker
```

Wait until ingestion shows `embedded`. Then:

### 6.3 Query the KB

```bash
KB_ID=$(curl -s http://localhost/api/v1/kbs \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")

curl -s -X POST http://localhost/api/v1/kbs/$KB_ID/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"What is RAG and how does it work?"}' \
  --no-buffer
```

The response is SSE — you should see `event: citations` followed by token chunks.

### 6.4 Swagger UI

Open `http://localhost/api/docs` in a browser. The spec should load (if it doesn't, the `/api/openapi.json` nginx fix didn't take effect).

### 6.5 Frontend

Open `http://localhost` — should show login page. Register the test user via the UI, then:
- Create a KB
- Add a URL source
- Ask a question in the Q&A tab

---

## Expected failure modes and fixes

### Ollama connection refused on first generation request

The `api` service doesn't depend on `ollama` being healthy (intentional — M0 didn't need it). If the first Q&A call fails with a connection error to Ollama, confirm `ollama` is running:
```bash
docker compose logs ollama | tail -20
curl http://localhost:11434/api/tags   # from inside the Docker network
```

### MinIO bucket access denied

MinIO initializes with the credentials from `.env`. If you see auth errors, confirm `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD` in `.env` match what `docker-compose.yml` passes to the `minio` service. The API creates the bucket (`knomms-media`) at startup — check `docker compose logs api | grep -i minio`.

### Frontend returns 502

Nuxt takes ~10s to start in production mode. Check:
```bash
docker compose logs frontend | tail -20
```

### Worker not processing jobs

```bash
docker compose logs worker | tail -30
```

The worker depends on `ollama` being healthy. If Ollama hasn't started, the worker container may not be running. Start `ollama` first, then:
```bash
docker compose restart worker
```

---

## Watching the full stack

```bash
docker compose logs -f --tail=50 api worker frontend
```

---

## Teardown (preserves data volumes)

```bash
docker compose down
```

To also destroy data:
```bash
docker compose down -v
```
