"""FastAPI router for login endpoint (no UI)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from triage_automation.application.dto.auth_models import LoginRequest, LoginResponse
from triage_automation.application.ports.auth_token_repository_port import (
    AuthTokenCreateInput,
    AuthTokenRepositoryPort,
)
from triage_automation.application.services.auth_service import AuthOutcome, AuthService
from triage_automation.infrastructure.security.token_service import OpaqueTokenService


def build_auth_router(
    *,
    auth_service: AuthService,
    auth_token_repository: AuthTokenRepositoryPort,
    token_service: OpaqueTokenService,
) -> APIRouter:
    """Build router exposing the minimal login endpoint."""

    router = APIRouter(tags=["auth"])

    @router.post("/auth/login", response_model=LoginResponse)
    async def login(payload: LoginRequest, request: Request) -> LoginResponse:
        ip_address = request.client.host if request.client is not None else None
        user_agent = request.headers.get("user-agent")

        auth_result = await auth_service.authenticate(
            email=payload.email,
            password=payload.password,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        if auth_result.outcome is AuthOutcome.INVALID_CREDENTIALS:
            raise HTTPException(status_code=401, detail="invalid credentials")
        if auth_result.outcome is AuthOutcome.INACTIVE_USER:
            raise HTTPException(status_code=403, detail="inactive user")

        user = auth_result.user
        if user is None:
            raise HTTPException(status_code=500, detail="authentication user missing")

        issued_token = token_service.issue_token()
        await auth_token_repository.create_token(
            AuthTokenCreateInput(
                user_id=user.user_id,
                token_hash=issued_token.token_hash,
                expires_at=issued_token.expires_at,
            )
        )

        return LoginResponse(
            token=issued_token.token,
            role=user.role,
            expires_at=issued_token.expires_at,
        )

    return router
