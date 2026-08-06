"""Organisation service — create/join/leave and admin membership management.

Single optional org per user (docs/09-organisations.md OQ-6): membership is
users.org_id/org_role, no join table. Services flush; routers commit.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organisation import Organisation
from app.models.team import Team, TeamMembership
from app.models.user import User

ORG_ROLES = frozenset({"admin", "member"})


def leave_blocked(is_admin: bool, admin_count: int, member_count: int) -> bool:
    """The last admin may not leave while other members remain — promote
    someone first. The sole member of an org may always leave."""
    return is_admin and admin_count == 1 and member_count > 1


def demote_blocked(target_is_admin: bool, admin_count: int) -> bool:
    """An org must keep at least one admin."""
    return target_is_admin and admin_count == 1


class OrganisationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_members(self, org_id: str) -> list[User]:
        result = await self.db.execute(
            select(User).where(User.org_id == org_id).order_by(User.created_at)
        )
        return list(result.scalars().all())

    async def get_own_org(self, user: User) -> Organisation:
        if user.org_id is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="You are not in an organisation")
        org = await self.db.get(Organisation, user.org_id)
        if org is None:  # FK guarantees this shouldn't happen, but stay defensive
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Organisation not found")
        return org

    async def create(self, user: User, name: str) -> Organisation:
        if user.org_id is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT, detail="Already in an organisation — leave it first"
            )
        org = Organisation(created_by=user.id, name=name)
        self.db.add(org)
        await self.db.flush()
        user.org_id = org.id
        user.org_role = "admin"
        return org

    async def join(self, user: User, invite_code: str) -> Organisation:
        if user.org_id is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT, detail="Already in an organisation — leave it first"
            )
        org = (
            await self.db.execute(
                select(Organisation).where(Organisation.invite_code == invite_code)
            )
        ).scalar_one_or_none()
        if org is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Invalid invite code")
        user.org_id = org.id
        user.org_role = "member"
        return org

    async def leave(self, user: User) -> None:
        org = await self.get_own_org(user)
        members = await self.get_members(org.id)
        admin_count = sum(1 for m in members if m.org_role == "admin")
        if leave_blocked(user.org_role == "admin", admin_count, len(members)):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="You are the last admin — promote another member before leaving",
            )
        await self._purge_team_memberships(user.id, org.id)
        user.org_id = None
        user.org_role = None

    async def rotate_invite(self, user: User) -> Organisation:
        org = await self._require_admin(user)
        org.invite_code = str(uuid.uuid4())
        return org

    async def update_member(self, user: User, target_id: str, org_role: str) -> None:
        if org_role not in ORG_ROLES:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"org_role must be one of: {sorted(ORG_ROLES)}",
            )
        org = await self._require_admin(user)
        target = await self._get_member(org, target_id)
        if target.org_role == org_role:
            return
        members = await self.get_members(org.id)
        admin_count = sum(1 for m in members if m.org_role == "admin")
        if org_role == "member" and demote_blocked(target.org_role == "admin", admin_count):
            raise HTTPException(
                status.HTTP_409_CONFLICT, detail="An organisation must keep at least one admin"
            )
        target.org_role = org_role

    async def remove_member(self, user: User, target_id: str) -> None:
        org = await self._require_admin(user)
        if target_id == user.id:
            raise HTTPException(
                status.HTTP_409_CONFLICT, detail="Use leave to remove yourself"
            )
        target = await self._get_member(org, target_id)
        await self._purge_team_memberships(target.id, org.id)
        target.org_id = None
        target.org_role = None

    async def _purge_team_memberships(self, user_id: str, org_id: str) -> None:
        """Team membership cannot outlive org membership (docs/10 §4): a user
        whose org_id goes NULL would otherwise keep team-grant access."""
        await self.db.execute(
            delete(TeamMembership).where(
                TeamMembership.user_id == user_id,
                TeamMembership.team_id.in_(select(Team.id).where(Team.org_id == org_id)),
            )
        )

    async def _require_admin(self, user: User) -> Organisation:
        org = await self.get_own_org(user)
        if user.org_role != "admin":
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Admin role required")
        return org

    async def _get_member(self, org: Organisation, target_id: str) -> User:
        target = await self.db.get(User, target_id)
        if target is None or target.org_id != org.id:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="No such member in your organisation"
            )
        return target
