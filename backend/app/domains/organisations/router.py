from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.auth import get_current_user
from app.deps.db import get_db
from app.domains.organisations.service import OrganisationService
from app.models.organisation import Organisation
from app.models.user import User
from app.schemas.organisation import (
    CreateOrgRequest,
    JoinOrgRequest,
    OrgMemberOut,
    OrgOut,
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
