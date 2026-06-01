"""Citation utilities — prompt injection and post-generation validation.

Contract with frontend useStreamingQuery.ts:
  SSE event 1:  event: citations\\ndata: <JSON dict>\\n\\n
  SSE events N: data: <token>\\n\\n          (no event: field → eventType='message')
  SSE end:      stream closed (no special event)
"""

import json
import re
from dataclasses import dataclass

from app.domains.retrieval.types import RetrievedChunk

_CITATION_PATTERN = re.compile(r"\[SOURCE:([a-f0-9\-]{36})\]")


@dataclass
class CitationData:
    chunk_id: str
    source_id: str
    locator: str
    excerpt: str  # first 200 chars of chunk text


def build_citations_dict(chunks: list[RetrievedChunk]) -> dict[str, dict]:
    """Build the citations dict sent as the first SSE event."""
    return {
        c.chunk_id: {
            "chunk_id": c.chunk_id,
            "source_id": c.source_id,
            "locator": c.locator,
            "excerpt": c.text[:200],
        }
        for c in chunks
    }


def build_rag_prompt(query: str, chunks: list[RetrievedChunk]) -> str:
    """Assemble a grounded generation prompt with inline passage blocks."""
    context_blocks = "\n\n".join(
        f"[PASSAGE chunk_id={c.chunk_id} locator={c.locator}]\n{c.text}\n[/PASSAGE]"
        for c in chunks
    )
    return f"""You are an AI assistant that answers questions based ONLY on the provided source passages.

Rules:
- Cite every factual claim using [SOURCE:chunk_id] notation.
- Only use chunk_ids that appear in the passages below — never invent them.
- If the passages do not contain enough information to answer, say so.
- Do not use knowledge outside the provided passages.

SOURCE PASSAGES:
{context_blocks}

QUESTION: {query}

ANSWER:"""


def extract_cited_ids(response_text: str) -> set[str]:
    """Extract all chunk_ids cited in a generated response."""
    return set(_CITATION_PATTERN.findall(response_text))


def validate_citations(response_text: str, valid_ids: set[str]) -> list[str]:
    """Return a list of chunk_ids cited in the response but NOT in valid_ids (hallucinated)."""
    cited = extract_cited_ids(response_text)
    return sorted(cited - valid_ids)


def citations_sse_event(citations_dict: dict) -> str:
    """Format the citations SSE event matching the frontend contract."""
    return f"event: citations\ndata: {json.dumps(citations_dict)}\n\n"


def token_sse_event(token: str) -> str:
    """Format a token SSE event (no event: field → frontend treats as default 'message')."""
    return f"data: {token}\n\n"
