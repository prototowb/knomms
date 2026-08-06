"""Grant routes, nested per grantable resource:

    GET/POST  /v1/{kbs|assets|harnesses}/{resource_id}/grants
    DELETE    /v1/{kbs|assets|harnesses}/{resource_id}/grants/{grant_id}

One registration helper instead of nine hand-written handlers — the bodies are
identical apart from the resource type.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.auth import get_current_user
from app.deps.db import get_db
from app.domains.acl.service import AclService
from app.models.user import User
from app.schemas.acl import CreateGrantRequest, GrantOut

router = APIRouter(tags=["sharing"])


def _grant_to_out(grant, label: str) -> GrantOut:
    return GrantOut(
        id=grant.id,
        principal_type=grant.principal_type,
        principal_id=grant.principal_id,
        principal_label=label,
        permission=grant.permission,
        created_at=grant.created_at,
    )


def _register(prefix: str, resource_type: str) -> None:
    @router.get(
        f"/{prefix}/{{resource_id}}/grants",
        response_model=list[GrantOut],
        name=f"list_{resource_type}_grants",
        summary=f"List grants on a {resource_type} (owner only)",
    )
    async def list_grants(
        resource_id: str,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
    ) -> list[GrantOut]:
        pairs = await AclService(db).list_grants(user, resource_type, resource_id)
        return [_grant_to_out(g, label) for g, label in pairs]

    @router.post(
        f"/{prefix}/{{resource_id}}/grants",
        response_model=GrantOut,
        status_code=status.HTTP_201_CREATED,
        name=f"upsert_{resource_type}_grant",
        summary=f"Share a {resource_type} with a user (by handle) or team (owner only; POST upserts the permission)",
    )
    async def upsert_grant(
        resource_id: str,
        req: CreateGrantRequest,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
    ) -> GrantOut:
        grant, label = await AclService(db).upsert_grant(
            user, resource_type, resource_id, req.principal_type, req.principal, req.permission
        )
        await db.commit()
        return _grant_to_out(grant, label)

    @router.delete(
        f"/{prefix}/{{resource_id}}/grants/{{grant_id}}",
        status_code=status.HTTP_204_NO_CONTENT,
        name=f"revoke_{resource_type}_grant",
        summary=f"Revoke a grant on a {resource_type} (owner only)",
    )
    async def revoke_grant(
        resource_id: str,
        grant_id: str,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
    ) -> None:
        await AclService(db).revoke_grant(user, resource_type, resource_id, grant_id)
        await db.commit()


_register("kbs", "kb")
_register("assets", "asset")
_register("harnesses", "harness")
