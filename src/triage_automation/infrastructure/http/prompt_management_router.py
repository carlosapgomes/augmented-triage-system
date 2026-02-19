"""FastAPI router for admin prompt-management endpoints."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

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
    SESSION_COOKIE_NAME,
    InvalidAuthTokenError,
    MissingAuthTokenError,
    WidgetAuthGuard,
)
from triage_automation.infrastructure.http.shell_context import build_shell_context

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def build_prompt_management_router(
    *,
    prompt_management_service: PromptManagementService,
    auth_guard: WidgetAuthGuard,
) -> APIRouter:
    """Build router exposing prompt-management admin APIs and HTML pages."""

    templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))
    router = APIRouter(tags=["prompt-management"])

    @router.get(
        "/admin/prompts",
        response_class=HTMLResponse,
        include_in_schema=False,
        response_model=None,
    )
    async def render_prompt_management_page(request: Request) -> Response:
        """Render prompt-management page for authenticated admin users."""

        authenticated_user = await _require_admin_user_for_html(
            auth_guard=auth_guard,
            request=request,
        )
        if isinstance(authenticated_user, RedirectResponse):
            return authenticated_user

        items = await prompt_management_service.list_versions()
        prompts_by_name: dict[str, list[PromptVersionItem]] = {}
        for item in items:
            prompts_by_name.setdefault(item.name, []).append(
                PromptVersionItem(name=item.name, version=item.version, is_active=item.is_active)
            )

        return templates.TemplateResponse(
            request=request,
            name="dashboard/prompts_admin.html",
            context={
                **build_shell_context(
                    page_title="Gestao de Prompts",
                    active_nav="prompts",
                    user=authenticated_user,
                ),
                "prompts_by_name": prompts_by_name,
                "activated_name": request.query_params.get("activated_name", ""),
                "activated_version": request.query_params.get("activated_version", ""),
                "created_name": request.query_params.get("created_name", ""),
                "created_version": request.query_params.get("created_version", ""),
                "error_message": request.query_params.get("error", ""),
            },
        )

    @router.get(
        "/admin/prompts/{prompt_name}/versions/{version}",
        response_class=HTMLResponse,
        include_in_schema=False,
        response_model=None,
    )
    async def render_prompt_version_content_page(
        request: Request,
        prompt_name: str,
        version: int,
    ) -> Response:
        """Render one prompt version with immutable content and create-new-version action."""

        authenticated_user = await _require_admin_user_for_html(
            auth_guard=auth_guard,
            request=request,
        )
        if isinstance(authenticated_user, RedirectResponse):
            return authenticated_user

        item = await prompt_management_service.get_version(
            prompt_name=prompt_name,
            version=version,
        )
        if item is None:
            return RedirectResponse(
                url=f"/admin/prompts?{urlencode({'error': 'Versao de prompt nao encontrada.'})}",
                status_code=303,
            )

        return templates.TemplateResponse(
            request=request,
            name="dashboard/prompt_version_detail.html",
            context={
                **build_shell_context(
                    page_title="Conteudo do Prompt",
                    active_nav="prompts",
                    user=authenticated_user,
                ),
                "prompt_name": item.name,
                "version": item.version,
                "is_active": item.is_active,
                "content": item.content,
                "error_message": request.query_params.get("error", ""),
            },
        )

    @router.post(
        "/admin/prompts/{prompt_name}/activate-form",
        response_class=HTMLResponse,
        include_in_schema=False,
        response_model=None,
    )
    async def activate_prompt_version_from_page(request: Request, prompt_name: str) -> Response:
        """Activate a prompt version from the server-rendered admin page."""

        authenticated_user = await _require_admin_user_for_html(
            auth_guard=auth_guard,
            request=request,
        )
        if isinstance(authenticated_user, RedirectResponse):
            return authenticated_user

        fields = await _read_form_fields(request=request)
        version = _read_positive_int_field(fields=fields, key="version")
        if version is None:
            return RedirectResponse(
                url=f"/admin/prompts?{urlencode({'error': 'Versao invalida.'})}",
                status_code=303,
            )

        try:
            activated = await prompt_management_service.activate_version(
                prompt_name=prompt_name,
                version=version,
                actor_user_id=authenticated_user.user_id,
            )
        except PromptVersionNotFoundError:
            return RedirectResponse(
                url=f"/admin/prompts?{urlencode({'error': 'Versao de prompt nao encontrada.'})}",
                status_code=303,
            )

        query_string = urlencode(
            {
                "activated_name": activated.name,
                "activated_version": activated.version,
            }
        )
        return RedirectResponse(url=f"/admin/prompts?{query_string}", status_code=303)

    @router.post(
        "/admin/prompts/{prompt_name}/create-form",
        response_class=HTMLResponse,
        include_in_schema=False,
        response_model=None,
    )
    async def create_prompt_version_from_page(request: Request, prompt_name: str) -> Response:
        """Create new immutable prompt version from HTML form content."""

        authenticated_user = await _require_admin_user_for_html(
            auth_guard=auth_guard,
            request=request,
        )
        if isinstance(authenticated_user, RedirectResponse):
            return authenticated_user

        fields = await _read_form_fields(request=request)
        source_version = _read_positive_int_field(fields=fields, key="source_version")
        if source_version is None:
            return RedirectResponse(
                url=f"/admin/prompts?{urlencode({'error': 'Versao de origem invalida.'})}",
                status_code=303,
            )
        content = fields.get("content", "").strip()
        if not content:
            return RedirectResponse(
                url=(
                    f"/admin/prompts/{prompt_name}/versions/{source_version}?"
                    f"{urlencode({'error': 'Conteudo do prompt nao pode ficar vazio.'})}"
                ),
                status_code=303,
            )

        try:
            created = await prompt_management_service.create_version(
                prompt_name=prompt_name,
                source_version=source_version,
                content=content,
                actor_user_id=authenticated_user.user_id,
            )
        except PromptVersionNotFoundError:
            return RedirectResponse(
                url=(
                    f"/admin/prompts/{prompt_name}/versions/{source_version}?"
                    f"{urlencode({'error': 'Versao de origem nao encontrada.'})}"
                ),
                status_code=303,
            )

        query_string = urlencode(
            {
                "created_name": created.name,
                "created_version": created.version,
            }
        )
        return RedirectResponse(url=f"/admin/prompts?{query_string}", status_code=303)

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
            authorization_header=request.headers.get("authorization"),
            session_token=request.cookies.get(SESSION_COOKIE_NAME),
        )
    except MissingAuthTokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except InvalidAuthTokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except UnknownRoleAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RoleNotAuthorizedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


async def _require_admin_user_for_html(
    *,
    auth_guard: WidgetAuthGuard,
    request: Request,
) -> UserRecord | RedirectResponse:
    """Resolve and authorize admin caller for HTML prompt-management routes."""

    try:
        return await auth_guard.require_admin_user(
            authorization_header=request.headers.get("authorization"),
            session_token=request.cookies.get(SESSION_COOKIE_NAME),
        )
    except MissingAuthTokenError:
        return RedirectResponse(url="/login", status_code=303)
    except InvalidAuthTokenError:
        return RedirectResponse(url="/login", status_code=303)
    except UnknownRoleAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RoleNotAuthorizedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


async def _read_form_fields(*, request: Request) -> dict[str, str]:
    """Parse URL-encoded HTML form payload into first-value field mapping."""

    body = await request.body()
    parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    return {key: values[0] if values else "" for key, values in parsed.items()}


def _read_positive_int_field(*, fields: dict[str, str], key: str) -> int | None:
    """Parse one positive integer field from decoded form mapping."""

    raw_version = fields.get(key, "").strip()
    if not raw_version or not raw_version.isdigit():
        return None
    version = int(raw_version)
    if version <= 0:
        return None
    return version
