from dataclasses import dataclass


@dataclass
class RetrievedChunk:
    chunk_id: str
    source_id: str
    locator: str
    text: str
    score: float  # cosine distance (lower = more similar; 0 = identical)
