from datetime import datetime

from pydantic import BaseModel

_ASSET_TYPES = {"system_prompt", "few_shot_set", "eval_suite", "chain_spec", "tool_spec"}
_VISIBILITIES = {"private", "team", "public"}


class CreateAssetRequest(BaseModel):
    title: str
    description: str = ""
    asset_type: str
    visibility: str = "private"


class AddVersionRequest(BaseModel):
    content: str
    rationale: str = ""
    tags: list[str] = []
    model_pin: str | None = None


class AssetVersionOut(BaseModel):
    id: str
    asset_id: str
    version_num: int
    content: str
    content_hash: str
    rationale: str
    tags: list | None = None
    model_pin: str | None = None
    status: str
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AssetOwnerOut(BaseModel):
    id: str
    handle: str
    display_name: str

    model_config = {"from_attributes": True}


class AssetOut(BaseModel):
    id: str
    title: str
    description: str
    asset_type: str
    visibility: str
    fork_count: int
    forked_from_id: str | None = None
    fork_lineage: list[str] = []
    created_at: datetime
    updated_at: datetime
    owner: AssetOwnerOut | None = None
    versions: list[AssetVersionOut] = []

    model_config = {"from_attributes": True}


class AssetSummary(BaseModel):
    id: str
    title: str
    description: str
    asset_type: str
    visibility: str
    fork_count: int
    created_at: datetime
    owner: AssetOwnerOut | None = None
    version_count: int = 0

    model_config = {"from_attributes": True}
