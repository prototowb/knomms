from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.db import engine
from app.core.redis import close_redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Ensure the MinIO bucket exists before the first request. This is safe to
    # call every startup — it's a no-op if the bucket already exists.
    from app.core.storage import ensure_bucket
    from app.core.config import settings
    try:
        await ensure_bucket(settings.minio_bucket)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("MinIO bucket init failed: %s", exc)

    yield
    # shutdown
    await close_redis()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Knowledge Comms API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:80"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _register_routers(app)
    return app


def _register_routers(app: FastAPI) -> None:
    from app.domains.identity.router import router as identity_router
    from app.domains.ingestion.router import router as ingestion_router
    from app.domains.generation.router import router as generation_router
    from app.domains.learning.router import router as learning_router
    from app.domains.curation.router import router as curation_router
    from app.domains.knowledge_base.router import router as kb_router
    from app.domains.assets.router import router as assets_router
    from app.domains.harnesses.router import router as harnesses_router
    from app.domains.organisations.router import router as organisations_router
    from app.domains.acl.router import router as acl_router

    app.include_router(identity_router, prefix="/v1")
    app.include_router(ingestion_router, prefix="/v1")
    app.include_router(generation_router, prefix="/v1")
    app.include_router(learning_router, prefix="/v1")
    app.include_router(curation_router, prefix="/v1")
    app.include_router(kb_router, prefix="/v1")
    app.include_router(assets_router, prefix="/v1")
    app.include_router(harnesses_router, prefix="/v1")
    app.include_router(organisations_router, prefix="/v1")
    app.include_router(acl_router, prefix="/v1")


app = create_app()


@app.get("/health", tags=["ops"])
async def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}
