"""Teams — named member subsets used as ACL principals (docs/10-teams-and-acls.md).

Teams carry no visibility semantics (OQ-14). Any org member may create one;
the creator and org admins manage it (OQ-15). Services flush; routers commit.
"""

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.acl import AclGrant
from app.models.team import Team, TeamMembership
from app.models.user import User


def team_manage_allowed(is_org_admin: bool, is_creator: bool) -> bool:
    """Creator and org admins manage a team; plain members only view/leave."""
    return is_org_admin or is_creator


class TeamService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, user: User, name: str) -> Team:
        org_id = self._require_org(user)
        duplicate = (
            await self.db.execute(
                select(Team.id).where(Team.org_id == org_id, Team.name == name)
            )
        ).scalar_one_or_none()
        if duplicate is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT, detail="A team with that name already exists"
            )
        team = Team(org_id=org_id, name=name, created_by=user.id)
        self.db.add(team)
        await self.db.flush()
        self.db.add(TeamMembership(team_id=team.id, user_id=user.id, added_by=user.id))
        await self.db.flush()
        return team

    async def list_for_org(self, user: User) -> list[Team]:
        org_id = self._require_org(user)
        result = await self.db.execute(
            select(Team)
            .where(Team.org_id == org_id)
            .options(selectinload(Team.memberships))
            .order_by(Team.created_at)
        )
        return list(result.scalars().all())

    async def get_team(self, user: User, team_id: str) -> Team:
        """Any member of the team's org may view it."""
        org_id = self._require_org(user)
        team = (
            await self.db.execute(
                select(Team)
                .where(Team.id == team_id, Team.org_id == org_id)
                .options(
                    selectinload(Team.memberships).selectinload(TeamMembership.user)
                )
                # membership rows are inserted/deleted by FK, not via the
                # relationship — force-refresh the loaded collection
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        if team is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Team not found")
        return team

    async def rename(self, user: User, team_id: str, name: str) -> Team:
        team = await self.get_team(user, team_id)
        self._require_manager(user, team)
        duplicate = (
            await self.db.execute(
                select(Team.id).where(
                    Team.org_id == team.org_id, Team.name == name, Team.id != team.id
                )
            )
        ).scalar_one_or_none()
        if duplicate is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT, detail="A team with that name already exists"
            )
        team.name = name
        return team

    async def delete(self, user: User, team_id: str) -> None:
        team = await self.get_team(user, team_id)
        self._require_manager(user, team)
        # Grants to a deleted team must not linger (docs/10 §5) — acl_grants has
        # no FK on principal_id, so this is the service's job
        await self.db.execute(
            delete(AclGrant).where(
                AclGrant.principal_type == "team", AclGrant.principal_id == team.id
            )
        )
        await self.db.delete(team)

    async def add_member(self, user: User, team_id: str, target_id: str) -> Team:
        team = await self.get_team(user, team_id)
        self._require_manager(user, team)
        target = await self.db.get(User, target_id)
        if target is None or target.org_id != team.org_id:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Target user is not a member of your organisation",
            )
        if any(m.user_id == target_id for m in team.memberships):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Already a team member")
        self.db.add(TeamMembership(team_id=team.id, user_id=target_id, added_by=user.id))
        await self.db.flush()
        return await self.get_team(user, team_id)

    async def remove_member(self, user: User, team_id: str, target_id: str) -> Team:
        team = await self.get_team(user, team_id)
        if target_id != user.id:  # leaving a team yourself needs no manager rights
            self._require_manager(user, team)
        membership = next((m for m in team.memberships if m.user_id == target_id), None)
        if membership is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No such team member")
        await self.db.delete(membership)
        await self.db.flush()
        return await self.get_team(user, team_id)

    def _require_org(self, user: User) -> str:
        if user.org_id is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="You are not in an organisation")
        return user.org_id

    def _require_manager(self, user: User, team: Team) -> None:
        if not team_manage_allowed(user.org_role == "admin", team.created_by == user.id):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, detail="Team creator or org admin required"
            )
