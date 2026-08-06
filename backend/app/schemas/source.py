from datetime import datetime

from pydantic import BaseModel, HttpUrl


class SourceSubmit(BaseModel):
    url: HttpUrl | None = None
    kb_id: str | None = None   # auto-creates default KB if absent


class SourceOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    type: str
    title: str
    ingestion_status: str
    kb_id: str
    raw_url: str | None = None  # deep-link target for video ts: locators (OQ-61)
    created_at: datetime


class SourceStatusOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    type: str
    title: str
    ingestion_status: str
    kb_id: str | None = None
    created_at: datetime
