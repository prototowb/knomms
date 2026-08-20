from datetime import datetime

from pydantic import BaseModel


class FeedOut(BaseModel):
    id: str
    kb_id: str
    slug: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SubscribeRequest(BaseModel):
    feed_url: str


class SubscriptionOut(BaseModel):
    id: str
    kb_id: str
    feed_url: str
    bundle_hash: str
    last_synced_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class SyncResultOut(BaseModel):
    changed: bool
    source_count: int = 0
    chunk_count: int = 0
    reindexing: bool = False
