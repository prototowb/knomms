from datetime import datetime

from pydantic import BaseModel


class KBOwnerOut(BaseModel):
    id: str
    handle: str
    display_name: str

    model_config = {"from_attributes": True}


class KnowledgeBaseOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    title: str
    visibility: str = "private"
    vector_namespace: str
    index_status: str
    created_at: datetime
    owner: KBOwnerOut | None = None


class PublicKBOut(BaseModel):
    """Explore listing shape — omits vector_namespace (internal detail)."""

    id: str
    title: str
    visibility: str
    index_status: str
    created_at: datetime
    owner: KBOwnerOut | None = None

    model_config = {"from_attributes": True}


class ChunkSearchResult(BaseModel):
    chunk_id: str
    source_id: str
    source_title: str
    source_type: str
    locator: str
    text: str
    score: float  # cosine distance for semantic mode (lower = more similar)
