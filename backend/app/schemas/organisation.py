from datetime import datetime

from pydantic import BaseModel, Field


class CreateOrgRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class JoinOrgRequest(BaseModel):
    invite_code: str = Field(min_length=1, max_length=36)


class UpdateMemberRequest(BaseModel):
    org_role: str


class OrgMemberOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    handle: str
    display_name: str
    org_role: str


class OrgOut(BaseModel):
    id: str
    name: str
    created_at: datetime
    members: list[OrgMemberOut]
    # Only present for admins — the router decides, not the schema
    invite_code: str | None = None
