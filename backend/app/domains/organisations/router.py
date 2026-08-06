from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.auth import get_current_user
from app.deps.db import get_db
from app.domains.organisations.service import OrganisationService
from app.domains.organisations.teams import TeamService, team_manage_allowed
from app.models.organisation import Organisation
from app.models.team import Team
from app.models.user import User
from app.schemas.organisation import (
    AddTeamMemberRequest,
    CreateOrgRequest,
    CreateTeamRequest,
    JoinOrgRequest,
    OrgMemberOut,
    OrgOut,
    RenameTeamRequest,
    TeamMemberOut,
    TeamOut,
    TeamSummaryOut,
    UpdateMemberRequest,
)

router = APIRouter(prefix="/orgs", tags=["organisations"])


async def _org_to_out(svc: OrganisationService, org: Organisation, user: User) -> OrgOut:
    members = await svc.get_members(org.id)
    return OrgOut(
        id=org.id,
        name=org.name,
        created_at=org.created_at,
        members=[OrgMemberOut.model_validate(m) for m in members],
        # The invite code is the join secret — members can see who's in, only
        # admins can let people in
        invite_code=org.invite_code if user.org_role == "admin" else None,
    )


@router.post("", response_model=OrgOut, status_code=status.HTTP_201_CREATED, summary="Create an organisation (caller becomes admin)")
async def create_org(
    req: CreateOrgRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrgOut:
    svc = OrganisationService(db)
    org = await svc.create(user, req.name)
    await db.commit()
    return await _org_to_out(svc, org, user)


@router.get("/me", response_model=OrgOut, summary="Get own organisation and member list")
async def get_my_org(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrgOut:
    svc = OrganisationService(db)
    org = await svc.get_own_org(user)
    return await _org_to_out(svc, org, user)


@router.post("/join", response_model=OrgOut, summary="Join an organisation by invite code")
async def join_org(
    req: JoinOrgRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrgOut:
    svc = OrganisationService(db)
    org = await svc.join(user, req.invite_code)
    await db.commit()
    return await _org_to_out(svc, org, user)


@router.post("/leave", status_code=status.HTTP_204_NO_CONTENT, summary="Leave your organisation")
async def leave_org(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    svc = OrganisationService(db)
    await svc.leave(user)
    await db.commit()


@router.post("/rotate-invite", response_model=OrgOut, summary="Rotate the invite code (admin only)")
async def rotate_invite(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrgOut:
    svc = OrganisationService(db)
    org = await svc.rotate_invite(user)
    await db.commit()
    return await _org_to_out(svc, org, user)


@router.patch("/members/{user_id}", response_model=OrgOut, summary="Promote or demote a member (admin only)")
async def update_member(
    user_id: str,
    req: UpdateMemberRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrgOut:
    svc = OrganisationService(db)
    await svc.update_member(user, user_id, req.org_role)
    await db.commit()
    org = await svc.get_own_org(user)
    return await _org_to_out(svc, org, user)


@router.delete("/members/{user_id}", response_model=OrgOut, summary="Remove a member (admin only)")
async def remove_member(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrgOut:
    svc = OrganisationService(db)
    await svc.remove_member(user, user_id)
    await db.commit()
    org = await svc.get_own_org(user)
    return await _org_to_out(svc, org, user)


# ── Teams (docs/10-teams-and-acls.md §5) ────────────────────────────────────


def _team_to_out(team: Team, user: User) -> TeamOut:
    return TeamOut(
        id=team.id,
        name=team.name,
        created_at=team.created_at,
        can_manage=team_manage_allowed(user.org_role == "admin", team.created_by == user.id),
        members=[
            TeamMemberOut(
                id=m.user.id, handle=m.user.handle, display_name=m.user.display_name
            )
            for m in team.memberships
        ],
    )


@router.post("/teams", response_model=TeamOut, status_code=status.HTTP_201_CREATED, summary="Create a team (creator auto-joins)")
async def create_team(
    req: CreateTeamRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TeamOut:
    svc = TeamService(db)
    team = await svc.create(user, req.name)
    await db.commit()
    return _team_to_out(await svc.get_team(user, team.id), user)


@router.get("/teams", response_model=list[TeamSummaryOut], summary="List your organisation's teams")
async def list_teams(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[TeamSummaryOut]:
    svc = TeamService(db)
    teams = await svc.list_for_org(user)
    return [
        TeamSummaryOut(
            id=t.id,
            name=t.name,
            member_count=len(t.memberships),
            is_member=any(m.user_id == user.id for m in t.memberships),
            can_manage=team_manage_allowed(user.org_role == "admin", t.created_by == user.id),
            created_at=t.created_at,
        )
        for t in teams
    ]


@router.get("/teams/{team_id}", response_model=TeamOut, summary="Get a team and its members")
async def get_team(
    team_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TeamOut:
    return _team_to_out(await TeamService(db).get_team(user, team_id), user)


@router.patch("/teams/{team_id}", response_model=TeamOut, summary="Rename a team (creator/org admin)")
async def rename_team(
    team_id: str,
    req: RenameTeamRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TeamOut:
    svc = TeamService(db)
    team = await svc.rename(user, team_id, req.name)
    await db.commit()
    return _team_to_out(await svc.get_team(user, team.id), user)


@router.delete("/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a team and its grants (creator/org admin)")
async def delete_team(
    team_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    await TeamService(db).delete(user, team_id)
    await db.commit()


@router.post("/teams/{team_id}/members", response_model=TeamOut, summary="Add an org member to a team (creator/org admin)")
async def add_team_member(
    team_id: str,
    req: AddTeamMemberRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TeamOut:
    svc = TeamService(db)
    team = await svc.add_member(user, team_id, req.user_id)
    await db.commit()
    return _team_to_out(team, user)


@router.delete("/teams/{team_id}/members/{user_id}", response_model=TeamOut, summary="Remove a team member (creator/org admin, or yourself)")
async def remove_team_member(
    team_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TeamOut:
    svc = TeamService(db)
    team = await svc.remove_member(user, team_id, user_id)
    await db.commit()
    return _team_to_out(team, user)
