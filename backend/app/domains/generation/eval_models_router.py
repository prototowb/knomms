"""GET /v1/eval-models — the compose page's single source of truth for eval
targets across enabled providers (docs/11-cloud-eval-adapter.md §5). The cloud
group appears only when the operator opted in; the response shape is stable
either way."""

import httpx
from fastapi import APIRouter, Depends

from app.core.config import settings
from app.deps.auth import get_current_user
from app.domains.generation import cloud
from app.models.user import User

router = APIRouter(tags=["eval-models"])


@router.get("/eval-models", summary="List available eval target models, grouped by provider")
async def list_eval_models(_user: User = Depends(get_current_user)) -> dict:
    providers: list[dict] = []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            resp.raise_for_status()
            ollama_models = [m["name"] for m in resp.json().get("models", [])]
    except Exception:
        ollama_models = []  # soft failure, same contract as the old /api/models BFF
    providers.append({"provider": "ollama", "models": ollama_models})

    if cloud.is_enabled():
        try:
            cloud_models = await cloud.list_models()
        except Exception:
            cloud_models = []
        providers.append({"provider": "anthropic", "models": cloud_models})

    return {"providers": providers}
