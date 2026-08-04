# Backend Architecture — Knowledge Comms

**Stack:** Python 3.12 + FastAPI + SQLAlchemy 2.0 (async) + pgvector + LangGraph  
**Version:** 0.1

---

## 1. Architecture Philosophy: Modular Monolith

The platform spec in `docs/05-platform-architecture.md` describes seven logical service domains (Ingestion, Retrieval, Generation, Learning, Curation, Identity, Notification). For a self-hosted deployment on Docker Compose, running these as seven separate Python processes would mean seven health checks, seven networking configurations, seven dependency graphs, and seven containers to operate — with no throughput benefit at self-hosted scale.

**Decision: one FastAPI application (`api`) with domain-organized modules, plus one separate ingestion worker process (`worker`).**

The logical boundaries are preserved as Python packages. The separation between `api` and `worker` exists for one concrete reason: ingestion jobs are CPU/IO-heavy background tasks that compete with interactive API request handling. They deserve their own process and their own resource limits in Docker Compose.

```
docker-compose services:
  api      ← FastAPI app (all HTTP + WebSocket endpoints)
  worker   ← Ingestion worker (Redis Streams consumer, same codebase)
```

Everything else (Retrieval, Generation, Learning, Curation, Identity, Notification) lives as modules inside `api`, callable as standard Python without HTTP hops.

---

## 2. Project Structure

```
backend/
├── pyproject.toml
├── alembic/
│   ├── env.py
│   └── versions/
├── app/
│   ├── main.py                  # FastAPI app factory, lifespan, router registration
│   ├── core/
│   │   ├── config.py            # Settings via pydantic-settings
│   │   ├── db.py                # SQLAlchemy async engine + session factory
│   │   ├── redis.py             # Redis connection pool
│   │   ├── storage.py           # MinIO client wrapper
│   │   └── security.py          # JWT encode/decode, password hashing
│   ├── deps/
│   │   ├── auth.py              # get_current_user, require_scope FastAPI deps
│   │   ├── db.py                # get_db_session dependency
│   │   └── pagination.py        # cursor-based pagination dep
│   ├── models/                  # SQLAlchemy ORM models (one file per domain)
│   │   ├── source.py
│   │   ├── chunk.py
│   │   ├── collection.py
│   │   ├── knowledge_base.py
│   │   ├── learning.py
│   │   └── user.py
│   ├── schemas/                 # Pydantic v2 request/response schemas
│   │   ├── source.py
│   │   ├── chunk.py
│   │   ├── collection.py
│   │   ├── knowledge_base.py
│   │   ├── learning.py
│   │   └── user.py
│   └── domains/                 # Business logic, one package per domain
│       ├── ingestion/
│       │   ├── router.py        # POST /sources, GET /sources/{id}
│       │   ├── service.py       # submit_source(), get_source_status()
│       │   ├── extractors/      # per-type extractors → RawBlock[]
│       │   │   ├── base.py
│       │   │   ├── pdf.py
│       │   │   ├── web.py
│       │   │   └── docx.py
│       │   └── chunker.py       # semantic chunking pipeline
│       ├── retrieval/
│       │   ├── router.py        # GET /kbs/{id}/search
│       │   ├── service.py       # hybrid_retrieve(), rerank()
│       │   └── pgvector.py      # pgvector query helpers
│       ├── generation/
│       │   ├── router.py        # POST /kbs/{id}/query (SSE streaming)
│       │   ├── service.py       # grounded_generate(), intent_classify()
│       │   ├── ollama.py        # async Ollama HTTP client wrapper
│       │   ├── citation.py      # citation injection + validation
│       │   └── faithfulness.py  # NLI fidelity scorer
│       ├── agents/
│       │   ├── runner.py        # AgentRunner: LangGraph wrapper + checkpoint
│       │   ├── synthesis.py     # Synthesis agent graph
│       │   ├── curriculum.py    # Curriculum agent graph
│       │   └── assessment.py    # Assessment agent graph
│       ├── learning/
│       │   ├── router.py        # /learning-paths, /modules, /assessments
│       │   └── service.py       # path generation, progress, mastery
│       ├── curation/
│       │   ├── router.py        # /collections, /boards, /fork
│       │   ├── service.py       # fork_collection(), board operations
│       │   └── presence.py      # WebSocket presence manager
│       ├── identity/
│       │   ├── router.py        # /auth/*, /users, /api-keys
│       │   └── service.py       # JWT issuance, user CRUD, follow graph
│       └── notifications/
│           ├── dispatcher.py    # event → delivery channel fan-out
│           └── channels/
│               ├── inapp.py
│               └── email.py
└── worker/
    ├── main.py                  # Redis Streams consumer entrypoint
    ├── pipeline.py              # orchestrates ingestion stages
    └── embed.py                 # batched embedding via Ollama
```

---

## 3. FastAPI App Setup

### App Factory and Lifespan

```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.db import engine
from app.core.redis import redis_pool
from app.core.storage import init_minio_buckets

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    await init_minio_buckets()
    await redis_pool.initialize()
    yield
    # shutdown
    await redis_pool.aclose()
    await engine.dispose()

def create_app() -> FastAPI:
    app = FastAPI(
        title="Knowledge Comms API",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
    )
    register_routers(app)
    register_middleware(app)
    return app

def register_routers(app: FastAPI) -> None:
    from app.domains.ingestion.router import router as ingestion_router
    from app.domains.retrieval.router import router as retrieval_router
    from app.domains.generation.router import router as generation_router
    from app.domains.learning.router import router as learning_router
    from app.domains.curation.router import router as curation_router
    from app.domains.identity.router import router as identity_router

    app.include_router(ingestion_router, prefix="/v1")
    app.include_router(retrieval_router, prefix="/v1")
    app.include_router(generation_router, prefix="/v1")
    app.include_router(learning_router, prefix="/v1")
    app.include_router(curation_router, prefix="/v1")
    app.include_router(identity_router, prefix="/v1")
```

### Configuration

All settings come from environment variables via `pydantic-settings`. One settings object, no global mutable state.

```python
# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # database
    database_url: str                       # postgresql+asyncpg://...
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # redis
    redis_url: str = "redis://redis:6379/0"

    # minio
    minio_endpoint: str = "http://minio:9000"
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str = "knomms-media"

    # ollama
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "mistral:7b-instruct"
    ollama_embed_model: str = "nomic-embed-text"
    max_concurrent_generations: int = 2

    # auth
    secret_key: str
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # ingestion
    max_upload_size_mb: int = 200
    crawl_rate_limit_rps: float = 1.0

settings = Settings()
```

---

## 4. Database Layer

### SQLAlchemy 2.0 Async

```python
# app/core/db.py
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine
)
from sqlalchemy.orm import DeclarativeBase

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

class Base(DeclarativeBase):
    pass
```

```python
# app/deps/db.py
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import AsyncSessionLocal

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### ORM Models with pgvector

```python
# app/models/chunk.py
from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base

class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # UUID as str
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    locator: Mapped[str] = mapped_column(String(128))          # "page:3", "ts:01:23:45"
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(768))
    embedding_model_id: Mapped[str] = mapped_column(String)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)

    source: Mapped["Source"] = relationship(back_populates="chunks")

    __table_args__ = (
        # HNSW index — created after initial data load for performance
        Index(
            "ix_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("ix_chunks_source_seq", "source_id", "seq"),
    )
```

pgvector ANN queries use SQLAlchemy's column operator overloading:

```python
# app/domains/retrieval/pgvector.py
from sqlalchemy import select, text
from pgvector.sqlalchemy import Vector
from app.models.chunk import Chunk

async def ann_search(
    db: AsyncSession,
    query_embedding: list[float],
    namespace_ids: list[str],
    top_k: int = 100,
    ef_search: int = 40,
) -> list[Chunk]:
    # set ef_search for this session (controls recall/latency trade-off)
    await db.execute(text(f"SET LOCAL hnsw.ef_search = {ef_search}"))

    stmt = (
        select(Chunk)
        .join(Chunk.source)
        .where(Source.vector_namespace.in_(namespace_ids))
        .order_by(Chunk.embedding.cosine_distance(query_embedding))
        .limit(top_k)
    )
    result = await db.execute(stmt)
    return result.scalars().all()
```

### Migrations with Alembic

Alembic manages all schema changes. The `env.py` is configured for async SQLAlchemy:

```python
# alembic/env.py (key parts)
from sqlalchemy.ext.asyncio import async_engine_from_config
import asyncio

def run_migrations_online():
    connectable = async_engine_from_config(config.get_section(config.config_ini_section))

    async def do_run():
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)

    asyncio.run(do_run())
```

Convention: every migration file is reversible (`upgrade` + `downgrade`). Migrations that add a new `pgvector` HNSW index use `CREATE INDEX CONCURRENTLY` via a raw SQL statement to avoid locking the `chunks` table during deployment.

---

## 5. API Patterns

### Router Structure

Each domain router uses a consistent shape:

```python
# app/domains/curation/router.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps.auth import get_current_user
from app.deps.db import get_db
from app.schemas.collection import CollectionCreate, CollectionOut, ForkRequest
from app.domains.curation.service import CurationService
from app.models.user import User

router = APIRouter(prefix="/collections", tags=["collections"])

@router.post("/", response_model=CollectionOut, status_code=status.HTTP_201_CREATED)
async def create_collection(
    body: CollectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CollectionOut:
    service = CurationService(db)
    return await service.create_collection(body, owner=current_user)

@router.post("/{collection_id}/fork", response_model=CollectionOut)
async def fork_collection(
    collection_id: str,
    body: ForkRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CollectionOut:
    service = CurationService(db)
    return await service.fork(collection_id, body, requester=current_user)
```

**Rules:**
- Routers own HTTP concerns only: status codes, request/response schemas, dependency injection.
- Business logic lives in the `service.py` class for that domain — never in the router function body.
- Services receive a `db: AsyncSession` at construction and own their own query logic. They do not call other domain services directly; they call lower-level shared modules (e.g., `retrieval.pgvector`, `generation.ollama`).

### Schemas (Pydantic v2)

Input and output schemas are separate types — never expose ORM models directly.

```python
# app/schemas/collection.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal

class CollectionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    visibility: Literal["private", "team", "public"] = "private"

class ForkRequest(BaseModel):
    title: str | None = None          # defaults to "{original} [fork]"
    exclude_source_ids: list[str] = []

class CollectionOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    title: str
    description: str
    visibility: str
    owner_user_id: str
    forked_from_id: str | None
    created_at: datetime
    source_count: int
```

### Streaming Responses (SSE)

Q&A queries stream tokens back to the Nuxt BFF via Server-Sent Events:

```python
# app/domains/generation/router.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.domains.generation.service import GenerationService

router = APIRouter(prefix="/kbs", tags=["generation"])

@router.post("/{kb_id}/query")
async def query_knowledge_base(
    kb_id: str,
    body: QueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    service = GenerationService(db)
    return StreamingResponse(
        service.stream_grounded_response(kb_id, body, current_user),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no"},  # disable Nginx buffering for SSE
    )
```

```python
# app/domains/generation/service.py
async def stream_grounded_response(self, kb_id, body, user):
    chunks = await self._retrieve(kb_id, body.query, user)
    citations = {c.id: CitationData.from_chunk(c) for c in chunks}

    # yield citations block first so the client can render inline refs immediately
    yield f"data: {json.dumps({'type': 'citations', 'data': citations})}\n\n"

    async for token in self.ollama.stream(
        model=settings.ollama_model,
        prompt=self._build_prompt(body.query, chunks),
    ):
        yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"

    yield "data: [DONE]\n\n"
```

### WebSocket Presence

```python
# app/domains/curation/router.py
from fastapi import WebSocket, WebSocketDisconnect
from app.domains.curation.presence import PresenceManager

presence = PresenceManager()   # singleton backed by Redis pub/sub

@router.websocket("/boards/{board_id}/presence")
async def board_presence(websocket: WebSocket, board_id: str):
    user_id = await _ws_auth(websocket)   # validates JWT from query param
    await presence.connect(websocket, board_id, user_id)
    try:
        while True:
            await websocket.receive_text()  # heartbeat ping; content ignored
    except WebSocketDisconnect:
        await presence.disconnect(board_id, user_id)
```

---

## 6. Ollama Client

A thin async wrapper around Ollama's HTTP API. Never calls Ollama directly from route handlers — always via this client in a service.

```python
# app/domains/generation/ollama.py
import httpx
from typing import AsyncIterator
from app.core.config import settings

class OllamaClient:
    def __init__(self):
        self._client = httpx.AsyncClient(
            base_url=settings.ollama_base_url,
            timeout=httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=5.0),
        )

    async def generate(self, model: str, prompt: str, **kwargs) -> str:
        response = await self._client.post("/api/generate", json={
            "model": model, "prompt": prompt, "stream": False, **kwargs
        })
        response.raise_for_status()
        return response.json()["response"]

    async def stream(self, model: str, prompt: str, **kwargs) -> AsyncIterator[str]:
        async with self._client.stream("POST", "/api/generate", json={
            "model": model, "prompt": prompt, "stream": True, **kwargs
        }) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    data = json.loads(line)
                    if not data.get("done"):
                        yield data["response"]

    async def embed(self, model: str, texts: list[str]) -> list[list[float]]:
        # Ollama embed endpoint processes one text at a time; batch externally
        embeddings = []
        for text in texts:
            response = await self._client.post("/api/embeddings", json={
                "model": model, "prompt": text
            })
            response.raise_for_status()
            embeddings.append(response.json()["embedding"])
        return embeddings

    async def ensure_model_loaded(self, model: str) -> None:
        """Warm-up probe — call at startup to pre-load model into VRAM."""
        await self.generate(model, "ping", options={"num_predict": 1})

    async def aclose(self):
        await self._client.aclose()

# module-level singleton — re-used across requests
ollama = OllamaClient()
```

The generation concurrency limit (from `MAX_CONCURRENT_GENERATIONS`) is enforced via an `asyncio.Semaphore` in `GenerationService`, not inside the client:

```python
# app/domains/generation/service.py
import asyncio

_generation_semaphore = asyncio.Semaphore(settings.max_concurrent_generations)

class GenerationService:
    async def stream_grounded_response(self, ...):
        async with _generation_semaphore:
            async for event in self._generate(...):
                yield event
```

---

## 7. Background Worker

The ingestion worker runs as a separate process that consumes from the `ingestion.jobs` Redis Stream. It shares all of `app/` — the same ORM models, settings, and Ollama client.

```python
# worker/main.py
import asyncio
from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.core.redis import get_redis
from worker.pipeline import run_ingestion_pipeline

STREAM_KEY = "ingestion.jobs"
CONSUMER_GROUP = "ingestion-workers"
CONSUMER_NAME = f"worker-{os.getpid()}"

async def consume():
    redis = await get_redis()
    # create consumer group if it doesn't exist
    try:
        await redis.xgroup_create(STREAM_KEY, CONSUMER_GROUP, id="0", mkstream=True)
    except Exception:
        pass  # group already exists

    while True:
        messages = await redis.xreadgroup(
            CONSUMER_GROUP, CONSUMER_NAME,
            {STREAM_KEY: ">"}, count=1, block=5000
        )
        if not messages:
            continue
        for _, entries in messages:
            for msg_id, fields in entries:
                try:
                    async with AsyncSessionLocal() as db:
                        await run_ingestion_pipeline(db, fields)
                    await redis.xack(STREAM_KEY, CONSUMER_GROUP, msg_id)
                except Exception as e:
                    # leave unacked — will be reclaimed after visibility timeout
                    logger.error(f"ingestion failed for {fields}: {e}")

if __name__ == "__main__":
    asyncio.run(consume())
```

### Ingestion Pipeline Stages

```python
# worker/pipeline.py
async def run_ingestion_pipeline(db: AsyncSession, job: dict) -> None:
    source_id = job["source_id"]
    source = await db.get(Source, source_id)

    await _update_status(db, source, "processing")

    # Stage 1: fetch / download raw content
    raw_content = await _fetch(source)
    await _store_raw(source, raw_content)           # write to MinIO

    # Stage 2: extract → RawBlock[]
    extractor = get_extractor(source.type)          # pdf.py, web.py, etc.
    raw_blocks = await extractor.extract(raw_content, source)

    # Stage 3: semantic chunking
    chunks = semantic_chunk(raw_blocks)             # app/domains/ingestion/chunker.py

    # Stage 4: dedup — skip blocks whose hash is already indexed
    new_chunks = await _dedup(db, source_id, chunks)

    await _update_status(db, source, "chunked")

    # Stage 5: embed in batches
    texts = [c.text for c in new_chunks]
    embeddings = await _batched_embed(texts)        # worker/embed.py

    # Stage 6: persist chunks + vectors
    await _persist_chunks(db, source_id, new_chunks, embeddings)
    await _update_status(db, source, "embedded")

    # Stage 7: publish event → notification fan-out
    await redis.publish(f"source.embedded", json.dumps({
        "source_id": source_id,
        "kb_ids": await _get_kb_ids_for_source(db, source_id),
    }))
```

```python
# worker/embed.py
EMBED_BATCH_SIZE = 32   # Ollama processes one text at a time; batch client-side

async def _batched_embed(texts: list[str]) -> list[list[float]]:
    embeddings = []
    for i in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[i : i + EMBED_BATCH_SIZE]
        batch_embeddings = await ollama.embed(settings.ollama_embed_model, batch)
        embeddings.extend(batch_embeddings)
    return embeddings
```

---

## 8. Authentication

JWT-based, no external auth provider.

```python
# app/core/security.py
from datetime import datetime, timedelta, timezone
import jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(user_id: str, namespaces: list[str]) -> str:
    payload = {
        "sub": user_id,
        "namespaces": namespaces,
        "exp": datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        ),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
```

```python
# app/deps/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import decode_token

bearer = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")

    user = await db.get(User, payload["sub"])
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

    # attach resolved namespaces to the user object for downstream use
    user._namespaces = payload["namespaces"]
    return user
```

The `namespaces` list is computed at token issuance by `IdentityService.issue_tokens()`, which joins the user's private KBs, team-shared KBs, and public KB namespace sentinel. The Retrieval Service reads `user._namespaces` when building vector queries — this is the enforcement point described in `docs/05-platform-architecture.md` §4.

---

## 9. LangGraph Agent Integration

Agents run via `AgentRunner`, a thin wrapper over LangGraph that handles checkpointing and HITL pauses.

```python
# app/domains/agents/runner.py
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import StateGraph

class AgentRunner:
    def __init__(self, db_url: str):
        self.checkpointer = AsyncPostgresSaver.from_conn_string(db_url)

    async def run(
        self,
        graph: StateGraph,
        initial_state: dict,
        thread_id: str,
        timeout_s: int = 120,
    ) -> AsyncIterator[dict]:
        compiled = graph.compile(checkpointer=self.checkpointer)
        config = {"configurable": {"thread_id": thread_id}}
        async with asyncio.timeout(timeout_s):
            async for event in compiled.astream(initial_state, config=config):
                yield event
```

Each agent (Synthesis, Curriculum, Assessment) defines its own `StateGraph` in its own module. The `AgentRunner` is instantiated once at app startup and injected into the agent services via dependency injection.

Agent state is checkpointed to PostgreSQL via `langgraph-checkpoint-postgres`. This means:
- Long-running synthesis jobs survive worker restarts
- HITL pauses store state at an `interrupt()` node; the user can resume hours later
- Agent run history is queryable for debugging

---

## 10. Testing

```python
# tests/conftest.py
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.main import create_app
from app.core.db import Base

# use a separate test database (same pgvector-enabled PostgreSQL)
TEST_DB_URL = "postgresql+asyncpg://kc:kc@localhost:5433/kc_test"

@pytest_asyncio.fixture(scope="session")
async def db_engine():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def db(db_engine):
    async with AsyncSession(db_engine) as session:
        yield session
        await session.rollback()

@pytest_asyncio.fixture
async def client(db):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
```

**Test strategy:**
- **Unit tests** for pure functions: chunker, citation validator, fidelity scorer, JWT encode/decode
- **Integration tests** with a real PostgreSQL + pgvector instance (via `testcontainers-python` or a dedicated test container in Docker Compose)
- **No mocking of the database** — pgvector queries must be tested against a real index to catch query plan issues
- **Ollama is mocked** in tests — the `OllamaClient` is replaced with a fixture that returns deterministic embeddings and completions; actual model inference is not part of the test suite

```python
# tests/domains/retrieval/test_hybrid_search.py
async def test_hybrid_retrieve_respects_namespace(client, db, seed_sources):
    # seed two sources in different namespaces
    public_source, private_source = await seed_sources(db)

    # query with only the public namespace
    results = await client.get(
        f"/v1/kbs/{public_kb_id}/search",
        params={"q": "test query"},
        headers={"Authorization": f"Bearer {public_only_token}"},
    )
    ids = [r["source_id"] for r in results.json()["results"]]
    assert private_source.id not in ids   # namespace isolation enforced
```

---

## 11. Key Dependencies

```toml
# pyproject.toml
[project]
name = "knomms-api"
requires-python = ">=3.12"
dependencies = [
    # web framework
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",

    # database
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.29",
    "pgvector>=0.3",
    "alembic>=1.13",

    # validation
    "pydantic>=2.7",
    "pydantic-settings>=2.3",

    # auth
    "pyjwt>=2.8",
    "passlib[bcrypt]>=1.7",

    # redis
    "redis[hiredis]>=5.0",

    # storage
    "miniopy-async>=1.20",          # async MinIO client

    # http client (Ollama, web scraping)
    "httpx>=0.27",
    "playwright>=1.44",             # JS-rendered web page scraping

    # document parsing
    "pdfminer.six>=20221105",
    "python-docx>=1.1",

    # NLI faithfulness scorer
    "sentence-transformers>=3.0",

    # agent orchestration
    "langgraph>=0.2",
    "langgraph-checkpoint-postgres>=1.0",

    # ingestion utilities
    "youtube-transcript-api>=0.6",
    "pyannote.audio>=3.1",          # speaker diarization (V2)
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "httpx>=0.27",                  # AsyncClient for tests
    "testcontainers[postgres]>=4.0",
    "ruff>=0.4",
    "mypy>=1.10",
]
```

---

## 12. MVP vs Full Build

### Ships in MVP

- All ingestion routes (PDF + web URL only)
- Grounded Q&A with SSE streaming and citation resolution
- Collection CRUD + fork action + ingestion job dispatch
- Knowledge base query endpoint with namespace enforcement
- Learning path generation (flat sequence, MC assessment only)
- JWT auth (issue, refresh, revoke)
- Ingestion worker (Redis Streams consumer, PDF + web extractors)
- Synthesis agent (LangGraph, single-hop, PostgreSQL checkpoints)
- NLI fidelity scorer on every generation

### Deferred to V2

- Video/audio ingestion (Whisper transcription worker)
- Speaker diarization (`pyannote.audio`)
- Curriculum agent + Assessment agent (LangGraph)
- Knowledge graph entity extraction
- Webhook delivery service
- Developer API key management
- Team workspace ACL management
- Open-ended assessment with rubric evaluation
- Passage annotation persistence
- Cohort enrollment and shared progress tracking
