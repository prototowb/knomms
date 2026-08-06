from datetime import datetime

from pydantic import BaseModel, Field


class CreateGrantRequest(BaseModel):
    principal_type: str  # 'user' | 'team' — validated in the service
    # A user handle for principal_type=user, a team id for principal_type=team
    principal: str = Field(min_length=1, max_length=100)
    permission: str  # 'viewer' | 'editor'


class GrantOut(BaseModel):
    id: str
    principal_type: str
    principal_id: str
    # Resolved display label — user handle or team name
    principal_label: str
    permission: str
    created_at: datetime
