"""Multi-source comparative synthesis (docs/16, OQ-63–67).

One grounded generation pass over balanced per-source retrieval — every
selected source is represented in the prompt or explicitly reported as
having nothing relevant. The SSE contract and citation notation are
byte-identical to Q&A, so the frontend streaming composable and the
citation validator reuse unchanged.
"""

from collections.abc import AsyncIterator

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.generation import citations as cit
from app.domains.generation.ollama import embed
from app.domains.knowledge_base.service import KnowledgeBaseService
from app.domains.retrieval.service import RetrievalService
from app.domains.retrieval.types import RetrievedChunk
from app.models.source import Source
from app.models.user import User

MIN_SOURCES = 2
MAX_SOURCES = 5


def check_source_selection(selected_ids: list[str], kb_source_ids: set[str]) -> str | None:
    """Guard decision for a synthesis request (OQ-65). Pure.

    Returns an error message, or None when the selection is valid.
    """
    if len(selected_ids) != len(set(selected_ids)):
        return "source_ids must not contain duplicates"
    if not (MIN_SOURCES <= len(selected_ids) <= MAX_SOURCES):
        return f"Select between {MIN_SOURCES} and {MAX_SOURCES} sources to compare"
    foreign = [s for s in selected_ids if s not in kb_source_ids]
    if foreign:
        return "source_ids must belong to this knowledge base"
    return None


def build_synthesis_prompt(question: str, groups: list[tuple[str, list[RetrievedChunk]]]) -> str:
    """Comparison prompt over per-source passage groups (OQ-66). Pure.

    Groups with no chunks are listed as having nothing relevant so the model
    accounts for them instead of silently comparing a subset.
    """
    sections = []
    for title, chunks in groups:
        if chunks:
            passages = "\n\n".join(
                f"[PASSAGE chunk_id={c.chunk_id} locator={c.locator}]\n{c.text}\n[/PASSAGE]"
                for c in chunks
            )
        else:
            passages = "(no relevant passages found in this source for the question)"
        sections.append(f"--- SOURCE: {title} ---\n{passages}")

    joined = "\n\n".join(sections)
    return f"""You are an AI assistant that compares what several sources say, based ONLY on the provided passages.

Rules:
- Compare the sources: where they agree, where they disagree, and what each says that the others do not.
- Attribute every claim to its source and cite it using [SOURCE:chunk_id] notation.
- Only use chunk_ids that appear in the passages below — never invent them.
- If a source has no relevant passages, say so explicitly rather than guessing its position.
- Do not use knowledge outside the provided passages.

SOURCE PASSAGES, GROUPED BY SOURCE:
{joined}

QUESTION: {question}

COMPARISON:"""


class SynthesisService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def stream_synthesis(
        self,
        kb_id: str,
        question: str,
        source_ids: list[str],
        user: User,
    ) -> AsyncIterator[str]:
        kb_svc = KnowledgeBaseService(self.db)
        kb = await kb_svc.get_readable_by_id(kb_id, user)
        if kb is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

        rows = (
            await self.db.execute(
                select(Source.id, Source.title).where(Source.kb_id == kb_id)
            )
        ).all()
        titles = {r.id: r.title for r in rows}

        error = check_source_selection(source_ids, set(titles))
        if error:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error)

        query_vec = (await embed([question]))[0]
        retrieval = RetrievalService(self.db)
        groups: list[tuple[str, list[RetrievedChunk]]] = []
        all_chunks: list[RetrievedChunk] = []
        for sid in source_ids:
            chunks = await retrieval.retrieve(
                query_vec,
                kb.vector_namespace,
                top_k=settings.synthesis_chunks_per_source,
                source_id=sid,
            )
            groups.append((titles[sid], chunks))
            all_chunks.extend(chunks)

        if not all_chunks:
            async def _empty():
                yield cit.citations_sse_event({})
                yield cit.token_sse_event(
                    "None of the selected sources contain passages relevant to this question."
                )
            return _empty()

        citations_dict = cit.build_citations_dict(all_chunks)
        prompt = build_synthesis_prompt(question, groups)

        # Reuse the Q&A stream generator — same semaphore, same events (OQ-67)
        from app.domains.generation.service import GenerationService

        return await GenerationService(self.db)._generate_stream(
            prompt, citations_dict, set(citations_dict.keys())
        )
