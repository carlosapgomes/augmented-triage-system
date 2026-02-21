"""FastAPI router for admin user-management HTML endpoints."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlencode
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from triage_automation.application.ports.user_repository_port import UserRecord
from triage_automation.application.services.access_guard_service import (
    RoleNotAuthorizedError,
    UnknownRoleAuthorizationError,
)
from triage_automation.application.services.user_management_service import (
    InvalidUserEmailError,
    InvalidUserPasswordError,
    LastActiveAdminError,
    SelfUserManagementError,
    UserCreateRequest,
    UserManagementAuthorizationError,
    UserManagementService,
    UserNotFoundError,
)
from triage_automation.domain.auth.roles import Role, UnknownRoleError
from triage_automation.infrastructure.http.auth_guard import (
    SESSION_COOKIE_NAME,
    InvalidAuthTokenError,
    MissingAuthTokenError,
    WidgetAuthGuard,
)
from triage_automation.infrastructure.http.shell_context import build_shell_context

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def build_user_management_router(
    *,
    user_management_service: UserManagementService,
    auth_guard: WidgetAuthGuard,
) -> APIRouter:
    """Build router exposing admin user-management HTML routes."""

    templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))
    router = APIRouter(tags=["user-management"])

    @router.get(
        "/admin/users",
        response_class=HTMLResponse,
        include_in_schema=False,
        response_model=None,
    )
    async def render_user_management_page(request: Request) -> Response:
        """Render user-management page for authenticated admin users."""

        authenticated_user = await _require_admin_user_for_html(
            auth_guard=auth_guard,
            request=request,
        )
        if isinstance(authenticated_user, RedirectResponse):
            return authenticated_user

        users = await user_management_service.list_users()
        return templates.TemplateResponse(
            request=request,
            name="dashboard/users_admin.html",
            context={
                **build_shell_context(
                    page_title="Gestao de Usuarios",
                    active_nav="users",
                    user=authenticated_user,
                ),
                "users": users,
                "created_email": request.query_params.get("created_email", ""),
                "updated_email": request.query_params.get("updated_email", ""),
                "updated_status": request.query_params.get("updated_status", ""),
                "error_message": request.query_params.get("error", ""),
            },
        )

    @router.post(
        "/admin/users",
        response_class=HTMLResponse,
        include_in_schema=False,
        response_model=None,
    )
    async def create_user_from_page(request: Request) -> Response:
        """Create user account from HTML form and redirect back to page."""

        authenticated_user = await _require_admin_user_for_html(
            auth_guard=auth_guard,
            request=request,
        )
        if isinstance(authenticated_user, RedirectResponse):
            return authenticated_user

        fields = await _read_form_fields(request=request)
        email = fields.get("email", "")
        password = fields.get("password", "")
        role_raw = fields.get("role", "").strip().lower()
        try:
            role = Role.from_value(role_raw)
        except UnknownRoleError:
            return RedirectResponse(
                url=f"/admin/users?{urlencode({'error': 'Perfil de usuario invalido.'})}",
                status_code=303,
            )

        try:
            created = await user_management_service.create_user(
                actor_user_id=authenticated_user.user_id,
                payload=UserCreateRequest(email=email, password=password, role=role),
            )
        except InvalidUserEmailError:
            return RedirectResponse(
                url=f"/admin/users?{urlencode({'error': 'Email nao pode ficar vazio.'})}",
                status_code=303,
            )
        except InvalidUserPasswordError:
            return RedirectResponse(
                url=f"/admin/users?{urlencode({'error': 'Senha nao pode ficar vazia.'})}",
                status_code=303,
            )
        except UserManagementAuthorizationError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

        return RedirectResponse(
            url=f"/admin/users?{urlencode({'created_email': created.email})}",
            status_code=303,
        )

    @router.post(
        "/admin/users/{user_id}/block",
        response_class=HTMLResponse,
        include_in_schema=False,
        response_model=None,
    )
    async def block_user_from_page(request: Request, user_id: UUID) -> Response:
        """Block target user account from HTML action."""

        authenticated_user = await _require_admin_user_for_html(
            auth_guard=auth_guard,
            request=request,
        )
        if isinstance(authenticated_user, RedirectResponse):
            return authenticated_user

        try:
            blocked = await user_management_service.block_user(
                actor_user_id=authenticated_user.user_id,
                user_id=user_id,
            )
        except UserNotFoundError:
            return RedirectResponse(
                url=f"/admin/users?{urlencode({'error': 'Usuario alvo nao encontrado.'})}",
                status_code=303,
            )
        except SelfUserManagementError:
            query = urlencode({"error": "Nao e permitido bloquear a propria conta."})
            return RedirectResponse(
                url=f"/admin/users?{query}",
                status_code=303,
            )
        except LastActiveAdminError:
            query = urlencode({"error": "Pelo menos um admin ativo deve permanecer."})
            return RedirectResponse(
                url=f"/admin/users?{query}",
                status_code=303,
            )
        except UserManagementAuthorizationError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

        query = urlencode(
            {"updated_email": blocked.email, "updated_status": blocked.account_status.value}
        )
        return RedirectResponse(url=f"/admin/users?{query}", status_code=303)

    @router.post(
        "/admin/users/{user_id}/activate",
        response_class=HTMLResponse,
        include_in_schema=False,
        response_model=None,
    )
    async def reactivate_user_from_page(request: Request, user_id: UUID) -> Response:
        """Reactivate target user account from HTML action."""

        authenticated_user = await _require_admin_user_for_html(
            auth_guard=auth_guard,
            request=request,
        )
        if isinstance(authenticated_user, RedirectResponse):
            return authenticated_user

        try:
            activated = await user_management_service.reactivate_user(
                actor_user_id=authenticated_user.user_id,
                user_id=user_id,
            )
        except UserNotFoundError:
            return RedirectResponse(
                url=f"/admin/users?{urlencode({'error': 'Usuario alvo nao encontrado.'})}",
                status_code=303,
            )
        except UserManagementAuthorizationError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

        query = urlencode(
            {"updated_email": activated.email, "updated_status": activated.account_status.value}
        )
        return RedirectResponse(url=f"/admin/users?{query}", status_code=303)

    @router.post(
        "/admin/users/{user_id}/remove",
        response_class=HTMLResponse,
        include_in_schema=False,
        response_model=None,
    )
    async def remove_user_from_page(request: Request, user_id: UUID) -> Response:
        """Remove target user account from HTML action."""

        authenticated_user = await _require_admin_user_for_html(
            auth_guard=auth_guard,
            request=request,
        )
        if isinstance(authenticated_user, RedirectResponse):
            return authenticated_user

        try:
            removed = await user_management_service.remove_user(
                actor_user_id=authenticated_user.user_id,
                user_id=user_id,
            )
        except UserNotFoundError:
            return RedirectResponse(
                url=f"/admin/users?{urlencode({'error': 'Usuario alvo nao encontrado.'})}",
                status_code=303,
            )
        except SelfUserManagementError:
            query = urlencode({"error": "Nao e permitido remover a propria conta."})
            return RedirectResponse(
                url=f"/admin/users?{query}",
                status_code=303,
            )
        except LastActiveAdminError:
            query = urlencode({"error": "Pelo menos um admin ativo deve permanecer."})
            return RedirectResponse(
                url=f"/admin/users?{query}",
                status_code=303,
            )
        except UserManagementAuthorizationError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

        query = urlencode(
            {"updated_email": removed.email, "updated_status": removed.account_status.value}
        )
        return RedirectResponse(url=f"/admin/users?{query}", status_code=303)

    return router


async def _require_admin_user_for_html(
    *,
    auth_guard: WidgetAuthGuard,
    request: Request,
) -> UserRecord | RedirectResponse:
    """Resolve and authorize admin caller for HTML user-management routes."""

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
