from datetime import datetime

from pydantic import BaseModel


class KnowledgeBaseOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    title: str
    vector_namespace: str
    index_status: str
    created_at: datetime


class ChunkSearchResult(BaseModel):
    chunk_id: str
    source_id: str
    source_title: str
    source_type: str
    locator: str
    text: str
    score: float  # cosine distance for semantic mode (lower = more similar)
