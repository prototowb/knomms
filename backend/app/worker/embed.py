"""Batched embedding via Ollama — used by the ingestion pipeline."""

from app.domains.generation.ollama import embed as ollama_embed

EMBED_BATCH_SIZE = 32


async def embed_chunks(texts: list[str]) -> list[list[float]]:
    """Embed texts in batches of EMBED_BATCH_SIZE, returning one vector per text."""
    all_embeddings: list[list[float]] = []
    for i in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[i : i + EMBED_BATCH_SIZE]
        batch_embeddings = await ollama_embed(batch)
        all_embeddings.extend(batch_embeddings)
    return all_embeddings
