from datetime import datetime

from pydantic import BaseModel


class SourceCardOut(BaseModel):
    id: str
    type: str
    title: str
    description: str
    raw_url: str | None = None
    ingestion_status: str

    model_config = {"from_attributes": True}


class BoardItemOut(BaseModel):
    id: str
    source_id: str
    note: str
    lane: str
    position: int
    added_at: datetime
    source: SourceCardOut | None = None

    model_config = {"from_attributes": True}


class CuratorOut(BaseModel):
    id: str
    handle: str
    display_name: str

    model_config = {"from_attributes": True}


class BoardOut(BaseModel):
    id: str
    title: str
    description: str
    visibility: str
    fork_count: int
    forked_from_id: str | None = None
    fork_lineage: list[str] = []
    layout_config: dict = {}
    ai_summary: str | None = None
    item_count: int = 0
    created_at: datetime
    updated_at: datetime
    owner: CuratorOut | None = None
    items: list[BoardItemOut] = []

    model_config = {"from_attributes": True}


class BoardSummary(BaseModel):
    id: str
    title: str
    description: str
    visibility: str
    fork_count: int
    item_count: int
    ai_summary: str | None = None
    created_at: datetime
    owner: CuratorOut | None = None

    model_config = {"from_attributes": True}


class CreateBoardRequest(BaseModel):
    title: str
    description: str = ""
    visibility: str = "private"
    layout_config: dict = {}


class ForkBoardRequest(BaseModel):
    new_title: str
    visibility: str = "private"


class AddSourceRequest(BaseModel):
    source_url: str
    note: str = ""
    lane: str = ""


class AddAssetRequest(BaseModel):
    asset_id: str
    version_num: int
    note: str = ""
    lane: str = ""


class CuratorProfileOut(BaseModel):
    handle: str
    display_name: str
    board_count: int
    boards: list[BoardSummary] = []
