"""Async Ollama HTTP client — generation and embedding."""

import json
from collections.abc import AsyncIterator

import httpx

from app.core.config import settings

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=settings.ollama_base_url,
            timeout=httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=5.0),
        )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def generate(prompt: str, model: str | None = None) -> str:
    """Single-shot generation — returns the full response text."""
    client = _get_client()
    resp = await client.post(
        "/api/generate",
        json={"model": model or settings.ollama_model, "prompt": prompt, "stream": False},
    )
    resp.raise_for_status()
    return resp.json()["response"]


async def stream(prompt: str, model: str | None = None) -> AsyncIterator[str]:
    """Stream generation tokens one by one."""
    client = _get_client()
    async with client.stream(
        "POST",
        "/api/generate",
        json={"model": model or settings.ollama_model, "prompt": prompt, "stream": True},
    ) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if not line:
                continue
            data = json.loads(line)
            if not data.get("done"):
                yield data.get("response", "")


async def embed(texts: list[str], model: str | None = None) -> list[list[float]]:
    """Embed a list of texts. Ollama processes one at a time; batching is client-side."""
    client = _get_client()
    embed_model = model or settings.ollama_embed_model
    embeddings: list[list[float]] = []
    for text in texts:
        resp = await client.post(
            "/api/embeddings",
            json={"model": embed_model, "prompt": text},
        )
        resp.raise_for_status()
        embeddings.append(resp.json()["embedding"])
    return embeddings
