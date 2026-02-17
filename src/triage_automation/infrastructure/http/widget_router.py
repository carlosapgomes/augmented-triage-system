"""FastAPI router for authenticated Room-2 widget bootstrap and submit endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from triage_automation.application.dto.webhook_models import TriageDecisionWebhookPayload
from triage_automation.application.dto.widget_models import (
    WidgetDecisionBootstrapRequest,
    WidgetDecisionBootstrapResponse,
    WidgetDecisionSubmitRequest,
    WidgetDecisionSubmitResponse,
)
from triage_automation.application.ports.case_repository_port import CaseRepositoryPort
from triage_automation.application.services.access_guard_service import AuthorizationError
from triage_automation.application.services.handle_doctor_decision_service import (
    HandleDoctorDecisionOutcome,
    HandleDoctorDecisionService,
)
from triage_automation.domain.case_status import CaseStatus
from triage_automation.infrastructure.http.auth_guard import (
    InvalidAuthTokenError,
    MissingAuthTokenError,
    WidgetAuthGuard,
)

_WIDGET_STATIC_DIR = (
    Path(__file__).resolve().parents[4] / "apps" / "bot_api" / "static" / "widget" / "room2"
)


def build_widget_router(
    *,
    decision_service: HandleDoctorDecisionService,
    case_repository: CaseRepositoryPort,
    auth_guard: WidgetAuthGuard,
) -> APIRouter:
    """Build router exposing widget bootstrap and submit endpoints."""

    router = APIRouter(tags=["widget"])

    @router.get("/widget/room2", response_class=HTMLResponse)
    async def widget_index() -> FileResponse:
        return _serve_widget_asset(filename="index.html", media_type="text/html; charset=utf-8")

    @router.get("/widget/room2/app.js")
    async def widget_app_js() -> FileResponse:
        return _serve_widget_asset(filename="app.js", media_type="application/javascript")

    @router.get("/widget/room2/styles.css")
    async def widget_styles_css() -> FileResponse:
        return _serve_widget_asset(filename="styles.css", media_type="text/css")

    @router.post(
        "/widget/room2/bootstrap",
        response_model=WidgetDecisionBootstrapResponse,
    )
    async def widget_bootstrap(
        payload: WidgetDecisionBootstrapRequest,
        authorization: Annotated[str | None, Header()] = None,
    ) -> WidgetDecisionBootstrapResponse:
        await _require_admin_user(auth_guard=auth_guard, authorization_header=authorization)

        snapshot = await case_repository.get_case_doctor_decision_snapshot(case_id=payload.case_id)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="case not found")
        if snapshot.status is not CaseStatus.WAIT_DOCTOR:
            raise HTTPException(status_code=409, detail="case not in WAIT_DOCTOR")

        return WidgetDecisionBootstrapResponse(
            case_id=snapshot.case_id,
            status=CaseStatus.WAIT_DOCTOR.value,
            doctor_decision=None,
            doctor_reason=None,
        )

    @router.post("/widget/room2/submit", response_model=WidgetDecisionSubmitResponse)
    async def widget_submit(
        payload: WidgetDecisionSubmitRequest,
        authorization: Annotated[str | None, Header()] = None,
    ) -> WidgetDecisionSubmitResponse:
        await _require_admin_user(auth_guard=auth_guard, authorization_header=authorization)

        webhook_payload = TriageDecisionWebhookPayload.model_validate(payload.model_dump())
        result = await decision_service.handle(webhook_payload)
        _raise_http_for_decision_outcome(result.outcome)
        return WidgetDecisionSubmitResponse(ok=True)

    return router


def _raise_http_for_decision_outcome(outcome: HandleDoctorDecisionOutcome) -> None:
    """Map existing decision service outcomes into HTTP response semantics."""

    if outcome is HandleDoctorDecisionOutcome.NOT_FOUND:
        raise HTTPException(status_code=404, detail="case not found")
    if outcome is HandleDoctorDecisionOutcome.WRONG_STATE:
        raise HTTPException(status_code=409, detail="case not in WAIT_DOCTOR")


async def _require_admin_user(
    *,
    auth_guard: WidgetAuthGuard,
    authorization_header: str | None,
) -> None:
    """Resolve authenticated user and enforce admin role for widget endpoints."""

    try:
        await auth_guard.require_admin_user(authorization_header=authorization_header)
    except MissingAuthTokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except InvalidAuthTokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _serve_widget_asset(*, filename: str, media_type: str) -> FileResponse:
    """Serve a static widget asset by filename from the bot-api static directory."""

    asset_path = _WIDGET_STATIC_DIR / filename
    if not asset_path.exists():
        raise HTTPException(status_code=500, detail=f"missing widget asset: {filename}")
    return FileResponse(path=asset_path, media_type=media_type)
