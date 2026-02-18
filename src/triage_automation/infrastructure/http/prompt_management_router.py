"""FastAPI router for admin prompt-management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from triage_automation.application.dto.prompt_management_models import (
    PromptActivationRequest,
    PromptVersionItem,
    PromptVersionListResponse,
)
from triage_automation.application.ports.user_repository_port import UserRecord
from triage_automation.application.services.access_guard_service import (
    RoleNotAuthorizedError,
    UnknownRoleAuthorizationError,
)
from triage_automation.application.services.prompt_management_service import (
    PromptManagementService,
    PromptVersionNotFoundError,
)
from triage_automation.infrastructure.http.auth_guard import (
    InvalidAuthTokenError,
    MissingAuthTokenError,
    WidgetAuthGuard,
)


def build_prompt_management_router(
    *,
    prompt_management_service: PromptManagementService,
    auth_guard: WidgetAuthGuard,
) -> APIRouter:
    """Build router exposing prompt-management admin APIs."""

    router = APIRouter(tags=["prompt-management"])

    @router.get("/admin/prompts/versions", response_model=PromptVersionListResponse)
    async def list_prompt_versions(request: Request) -> PromptVersionListResponse:
        """List all prompt versions with active-state markers."""

        await _require_admin_user(auth_guard=auth_guard, request=request)
        items = await prompt_management_service.list_versions()
        return PromptVersionListResponse(
            items=[
                PromptVersionItem(name=item.name, version=item.version, is_active=item.is_active)
                for item in items
            ]
        )

    @router.get("/admin/prompts/{prompt_name}/active", response_model=PromptVersionItem)
    async def get_active_prompt_version(request: Request, prompt_name: str) -> PromptVersionItem:
        """Return active prompt version metadata for one prompt name."""

        await _require_admin_user(auth_guard=auth_guard, request=request)
        item = await prompt_management_service.get_active_version(prompt_name=prompt_name)
        if item is None:
            raise HTTPException(status_code=404, detail="active prompt version not found")
        return PromptVersionItem(name=item.name, version=item.version, is_active=item.is_active)

    @router.post("/admin/prompts/{prompt_name}/activate", response_model=PromptVersionItem)
    async def activate_prompt_version(
        request: Request,
        prompt_name: str,
        payload: PromptActivationRequest,
    ) -> PromptVersionItem:
        """Activate selected prompt version for the provided prompt name."""

        authenticated_user = await _require_admin_user(auth_guard=auth_guard, request=request)
        try:
            activated = await prompt_management_service.activate_version(
                prompt_name=prompt_name,
                version=payload.version,
                actor_user_id=authenticated_user.user_id,
            )
        except PromptVersionNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return PromptVersionItem(
            name=activated.name,
            version=activated.version,
            is_active=activated.is_active,
        )

    return router


async def _require_admin_user(*, auth_guard: WidgetAuthGuard, request: Request) -> UserRecord:
    """Resolve and authorize admin caller for prompt-management operations."""

    try:
        return await auth_guard.require_admin_user(
            authorization_header=request.headers.get("authorization")
        )
    except MissingAuthTokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except InvalidAuthTokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except UnknownRoleAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RoleNotAuthorizedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
