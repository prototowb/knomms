from datetime import datetime

from pydantic import BaseModel, Field

# Size caps (docs/17, OQ-70) — a saved synthesis is a note, not a corpus
MAX_QUESTION_CHARS = 2_000
MAX_ANSWER_CHARS = 50_000
MAX_CITATIONS = 50


class SavedCitation(BaseModel):
    chunk_id: str = Field(max_length=36)
    source_id: str = Field(max_length=36)
    locator: str = Field(max_length=100)
    excerpt: str = Field(max_length=500)


class SaveSynthesisRequest(BaseModel):
    question: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)
    answer_text: str = Field(min_length=1, max_length=MAX_ANSWER_CHARS)
    source_ids: list[str]
    citations: list[SavedCitation] = Field(default_factory=list, max_length=MAX_CITATIONS)


class SynthesisOut(BaseModel):
    id: str
    kb_id: str
    question: str
    answer_text: str
    citations: list[dict] = []
    source_ids: list[str] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectSynthesisRequest(BaseModel):
    synthesis_id: str
    note: str = ""
    lane: str = "explore"
