from datetime import datetime
from typing import Any

from pydantic import BaseModel

_VISIBILITIES = {"private", "team", "public"}


class CreateHarnessRequest(BaseModel):
    title: str
    description: str = ""
    visibility: str = "private"


class ForkHarnessRequest(BaseModel):
    new_title: str
    visibility: str = "private"


class AddAssetVersionRequest(BaseModel):
    asset_version_id: str
    role: str
    position: int = 0


class SwapAssetVersionRequest(BaseModel):
    new_asset_version_id: str


class HarnessAssetOut(BaseModel):
    id: str
    harness_id: str
    asset_version_id: str
    role: str
    position: int
    added_at: datetime

    model_config = {"from_attributes": True}


class HarnessOwnerOut(BaseModel):
    id: str
    handle: str
    display_name: str

    model_config = {"from_attributes": True}


class HarnessOut(BaseModel):
    id: str
    title: str
    description: str
    visibility: str
    fork_count: int
    forked_from_id: str | None = None
    fork_lineage: list[str] = []
    study_kb_id: str | None = None
    created_at: datetime
    updated_at: datetime
    owner: HarnessOwnerOut | None = None
    assets: list[HarnessAssetOut] = []

    model_config = {"from_attributes": True}


class HarnessSummary(BaseModel):
    id: str
    title: str
    description: str
    visibility: str
    fork_count: int
    created_at: datetime
    owner: HarnessOwnerOut | None = None
    asset_count: int = 0

    model_config = {"from_attributes": True}


class SubmitEvalRequest(BaseModel):
    model: str
    provider: str = "ollama"  # 'ollama' | 'anthropic' — validated in the service


class StudyKBProjectOut(BaseModel):
    kb_id: str
    projected: int
    skipped: int


class StudyDocOut(BaseModel):
    doc_kind: str  # slot | eval_suite | eval_run
    ref_id: str
    source_id: str
    title: str
    ingestion_status: str


class StudyKBStatusOut(BaseModel):
    kb_id: str
    docs: list[StudyDocOut] = []


class EvalRunOut(BaseModel):
    id: str
    harness_id: str
    model_pin: str
    provider: str = "ollama"
    status: str
    metrics: Any | None = None
    eval_suite_version_id: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
