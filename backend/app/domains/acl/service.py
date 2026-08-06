"""ACL grant management — owner-only sharing of KBs, assets, and harnesses
(docs/10-teams-and-acls.md OQ-16–19).

Grant *management* never relaxes to editors — an editor must not escalate.
Services flush; routers commit.
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.organisations.predicates import (
    GRANT_PERMISSIONS,
    GRANT_PRINCIPAL_TYPES,
)
from app.models.acl import AclGrant
from app.models.asset import Asset, Harness
from app.models.knowledge_base import KnowledgeBase
from app.models.team import Team
from app.models.user import User

# resource_type -> ORM model; all three have id + owner_user_id
_RESOURCE_MODELS = {"kb": KnowledgeBase, "asset": Asset, "harness": Harness}


def grant_upsert_allowed(is_owner: bool, principal_is_owner: bool) -> bool:
    """Only the owner grants, and granting to the owner is meaningless."""
    return is_owner and not principal_is_owner


class AclService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_grants(
        self, user: User, resource_type: str, resource_id: str
    ) -> list[tuple[AclGrant, str]]:
        """Grants with resolved principal labels (user handle / team name)."""
        await self._require_owned_resource(user, resource_type, resource_id)
        grants = list(
            (
                await self.db.execute(
                    select(AclGrant)
                    .where(
                        AclGrant.resource_type == resource_type,
                        AclGrant.resource_id == resource_id,
                    )
                    .order_by(AclGrant.created_at)
                )
            )
            .scalars()
            .all()
        )
        return [(g, await self._principal_label(g)) for g in grants]

    async def upsert_grant(
        self,
        user: User,
        resource_type: str,
        resource_id: str,
        principal_type: str,
        principal: str,
        permission: str,
    ) -> tuple[AclGrant, str]:
        """Create a grant, or update the permission if the principal already
        has one (documented POST-as-upsert, docs/10 §5)."""
        if permission not in GRANT_PERMISSIONS:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"permission must be one of: {sorted(GRANT_PERMISSIONS)}",
            )
        if principal_type not in GRANT_PRINCIPAL_TYPES:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"principal_type must be one of: {sorted(GRANT_PRINCIPAL_TYPES)}",
            )
        resource = await self._require_owned_resource(user, resource_type, resource_id)

        if principal_type == "user":
            target = (
                await self.db.execute(select(User).where(User.handle == principal))
            ).scalar_one_or_none()
            if target is None:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND, detail=f"No user with handle '{principal}'"
                )
            if not grant_upsert_allowed(True, target.id == resource.owner_user_id):
                raise HTTPException(
                    status.HTTP_409_CONFLICT, detail="The owner does not need a grant"
                )
            principal_id, label = target.id, target.handle
        else:
            # Teams are grantable only from the granter's own org (OQ-19)
            team = (
                await self.db.execute(
                    select(Team).where(Team.id == principal, Team.org_id == user.org_id)
                )
            ).scalar_one_or_none()
            if team is None or user.org_id is None:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND, detail="No such team in your organisation"
                )
            principal_id, label = team.id, team.name

        existing = (
            await self.db.execute(
                select(AclGrant).where(
                    AclGrant.resource_type == resource_type,
                    AclGrant.resource_id == resource_id,
                    AclGrant.principal_type == principal_type,
                    AclGrant.principal_id == principal_id,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            existing.permission = permission
            await self.db.flush()
            return existing, label

        grant = AclGrant(
            resource_type=resource_type,
            resource_id=resource_id,
            principal_type=principal_type,
            principal_id=principal_id,
            permission=permission,
            granted_by=user.id,
        )
        self.db.add(grant)
        await self.db.flush()
        return grant, label

    async def revoke_grant(
        self, user: User, resource_type: str, resource_id: str, grant_id: str
    ) -> None:
        await self._require_owned_resource(user, resource_type, resource_id)
        grant = (
            await self.db.execute(
                select(AclGrant).where(
                    AclGrant.id == grant_id,
                    AclGrant.resource_type == resource_type,
                    AclGrant.resource_id == resource_id,
                )
            )
        ).scalar_one_or_none()
        if grant is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Grant not found")
        await self.db.delete(grant)

    async def _require_owned_resource(
        self, user: User, resource_type: str, resource_id: str
    ):
        model = _RESOURCE_MODELS[resource_type]
        resource = await self.db.get(model, resource_id)
        if resource is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Resource not found")
        if resource.owner_user_id != user.id:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, detail="Only the owner manages sharing"
            )
        return resource

    async def _principal_label(self, grant: AclGrant) -> str:
        if grant.principal_type == "user":
            target = await self.db.get(User, grant.principal_id)
            return target.handle if target else "(deleted user)"
        team = await self.db.get(Team, grant.principal_id)
        return team.name if team else "(deleted team)"
