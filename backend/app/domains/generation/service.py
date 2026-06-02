"""Generation service — grounded Q&A with SSE streaming."""

import asyncio
from collections.abc import AsyncIterator

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.generation import citations as cit
from app.domains.generation.ollama import embed, stream
from app.domains.knowledge_base.service import KnowledgeBaseService
from app.domains.retrieval.service import RetrievalService
from app.models.user import User

# Max concurrent Ollama generation requests (matches docker-compose env var)
from app.core.config import settings

_generation_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _generation_semaphore
    if _generation_semaphore is None:
        _generation_semaphore = asyncio.Semaphore(settings.max_concurrent_generations)
    return _generation_semaphore


class GenerationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def stream_grounded_response(
        self,
        kb_id: str,
        query: str,
        user: User,
    ) -> AsyncIterator[str]:
        # Authorize: ownership check (not JWT namespaces — those aren't populated
        # for KBs created post-login in M1)
        kb_svc = KnowledgeBaseService(self.db)
        kb = await kb_svc.get_by_id(kb_id, user)
        if kb is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

        # Embed the query
        query_embeddings = await embed([query])
        query_vec = query_embeddings[0]

        # 3 chunks ≈ 1200 input tokens — keeps CPU prefill to ~30s.
        # top_k=10 exhausts the 4096-token context and top_k=5 still caused
        # 2+ minute TTFT on CPU; 3 is the practical limit for CPU inference.
        retrieval_svc = RetrievalService(self.db)
        chunks = await retrieval_svc.retrieve(query_vec, kb.vector_namespace, top_k=3)

        if not chunks:
            async def _empty():
                yield cit.citations_sse_event({})
                yield cit.token_sse_event("No relevant sources found in this knowledge base for your query.")
            return _empty()

        citations_dict = cit.build_citations_dict(chunks)
        valid_ids = set(citations_dict.keys())
        prompt = cit.build_rag_prompt(query, chunks)

        return await self._generate_stream(prompt, citations_dict, valid_ids)

    async def _generate_stream(
        self,
        prompt: str,
        citations_dict: dict,
        valid_ids: set[str],
    ) -> AsyncIterator[str]:
        async def _inner():
            # Send citations block first so the client can resolve inline refs
            yield cit.citations_sse_event(citations_dict)

            full_response = ""
            async with _get_semaphore():
                async for token in stream(prompt):
                    full_response += token
                    yield cit.token_sse_event(token)

            # Post-generation: log hallucinated citations (don't block the stream)
            hallucinated = cit.validate_citations(full_response, valid_ids)
            if hallucinated:
                # In M1, log and continue. M4 adds the fidelity block/warn UI.
                import logging
                logging.getLogger(__name__).warning(
                    "Hallucinated citation IDs in response: %s", hallucinated
                )

        return _inner()
