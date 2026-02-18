"""FastAPI router for browser-first login/logout session flow."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from triage_automation.application.ports.auth_token_repository_port import (
    AuthTokenCreateInput,
    AuthTokenRepositoryPort,
)
from triage_automation.application.ports.user_repository_port import UserRecord
from triage_automation.application.services.access_guard_service import (
    RoleNotAuthorizedError,
    UnknownRoleAuthorizationError,
)
from triage_automation.application.services.auth_service import AuthOutcome, AuthService
from triage_automation.infrastructure.http.auth_guard import (
    SESSION_COOKIE_NAME,
    InvalidAuthTokenError,
    MissingAuthTokenError,
    WidgetAuthGuard,
)
from triage_automation.infrastructure.security.token_service import OpaqueTokenService

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def build_web_session_router(
    *,
    auth_service: AuthService,
    auth_token_repository: AuthTokenRepositoryPort,
    token_service: OpaqueTokenService,
    auth_guard: WidgetAuthGuard,
) -> APIRouter:
    """Build router exposing browser login/logout and root landing redirects."""

    templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))
    router = APIRouter(tags=["web-session"])

    @router.get("/", include_in_schema=False)
    async def root(request: Request) -> RedirectResponse:
        authenticated_user, should_clear_cookie = await _resolve_authenticated_user(
            auth_guard=auth_guard,
            request=request,
        )
        if authenticated_user is not None:
            return RedirectResponse(url="/dashboard/cases", status_code=303)
        return _build_login_redirect(request=request, clear_session_cookie=should_clear_cookie)

    @router.get(
        "/login",
        response_class=HTMLResponse,
        include_in_schema=False,
        response_model=None,
    )
    async def render_login_page(request: Request) -> Response:
        authenticated_user, should_clear_cookie = await _resolve_authenticated_user(
            auth_guard=auth_guard,
            request=request,
        )
        if authenticated_user is not None:
            return RedirectResponse(url="/dashboard/cases", status_code=303)

        response = templates.TemplateResponse(
            request=request,
            name="session/login.html",
            context={"page_title": "Login Operacional", "error_message": None, "email_value": ""},
        )
        if should_clear_cookie:
            _delete_session_cookie(response=response, request=request)
        return response

    @router.post(
        "/login",
        response_class=HTMLResponse,
        include_in_schema=False,
        response_model=None,
    )
    async def submit_login(request: Request) -> Response:
        form_values = await _parse_login_form(request)
        email = form_values["email"]
        password = form_values["password"]

        if not email or not password:
            return templates.TemplateResponse(
                request=request,
                name="session/login.html",
                context={
                    "page_title": "Login Operacional",
                    "error_message": "Informe email e senha.",
                    "email_value": email,
                },
                status_code=401,
            )

        ip_address = request.client.host if request.client is not None else None
        user_agent = request.headers.get("user-agent")

        auth_result = await auth_service.authenticate(
            email=email,
            password=password,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        if auth_result.outcome is AuthOutcome.INVALID_CREDENTIALS:
            return templates.TemplateResponse(
                request=request,
                name="session/login.html",
                context={
                    "page_title": "Login Operacional",
                    "error_message": "Credenciais invalidas.",
                    "email_value": email,
                },
                status_code=401,
            )

        if auth_result.outcome is AuthOutcome.INACTIVE_USER:
            return templates.TemplateResponse(
                request=request,
                name="session/login.html",
                context={
                    "page_title": "Login Operacional",
                    "error_message": "Usuario inativo.",
                    "email_value": email,
                },
                status_code=403,
            )

        user = auth_result.user
        if user is None:
            return templates.TemplateResponse(
                request=request,
                name="session/login.html",
                context={
                    "page_title": "Login Operacional",
                    "error_message": "Falha interna de autenticacao.",
                    "email_value": email,
                },
                status_code=500,
            )

        issued_token = token_service.issue_token()
        await auth_token_repository.create_token(
            AuthTokenCreateInput(
                user_id=user.user_id,
                token_hash=issued_token.token_hash,
                expires_at=issued_token.expires_at,
            )
        )

        redirect = RedirectResponse(url="/dashboard/cases", status_code=303)
        _set_session_cookie(
            response=redirect,
            request=request,
            token=issued_token.token,
            expires_at=issued_token.expires_at,
        )
        return redirect

    @router.post("/logout", include_in_schema=False)
    async def submit_logout(request: Request) -> RedirectResponse:
        response = RedirectResponse(url="/login", status_code=303)
        _delete_session_cookie(response=response, request=request)
        return response

    return router


async def _resolve_authenticated_user(
    *,
    auth_guard: WidgetAuthGuard,
    request: Request,
) -> tuple[UserRecord | None, bool]:
    """Resolve current authenticated user for web routes."""

    try:
        user = await auth_guard.require_audit_user(
            authorization_header=request.headers.get("authorization"),
            session_token=request.cookies.get(SESSION_COOKIE_NAME),
        )
        return user, False
    except MissingAuthTokenError:
        return None, False
    except InvalidAuthTokenError:
        return None, True
    except UnknownRoleAuthorizationError:
        return None, True
    except RoleNotAuthorizedError:
        return None, True


def _build_login_redirect(*, request: Request, clear_session_cookie: bool) -> RedirectResponse:
    """Build redirect response to login with optional cookie deletion."""

    response = RedirectResponse(url="/login", status_code=303)
    if clear_session_cookie:
        _delete_session_cookie(response=response, request=request)
    return response


def _set_session_cookie(
    *,
    response: RedirectResponse,
    request: Request,
    token: str,
    expires_at: datetime,
) -> None:
    """Set secure session cookie aligned with token expiration."""

    now = datetime.now(tz=UTC)
    max_age = max(int((expires_at - now).total_seconds()), 0)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=max_age,
        expires=expires_at,
        path="/",
        secure=request.url.scheme == "https",
        httponly=True,
        samesite="lax",
    )


def _delete_session_cookie(*, response: RedirectResponse | HTMLResponse, request: Request) -> None:
    """Delete session cookie using current request security mode."""

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=request.url.scheme == "https",
        httponly=True,
        samesite="lax",
    )


async def _parse_login_form(request: Request) -> dict[str, str]:
    """Parse urlencoded login form body into normalized credentials."""

    body = await request.body()
    parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    email = parsed.get("email", [""])[0].strip().lower()
    password = parsed.get("password", [""])[0]
    return {"email": email, "password": password}
