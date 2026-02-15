"""bot-api entrypoint and webhook callback endpoint wiring."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from pydantic import ValidationError

from triage_automation.application.dto.webhook_models import (
    TriageDecisionWebhookPayload,
    TriageDecisionWebhookResponse,
)
from triage_automation.application.services.handle_doctor_decision_service import (
    HandleDoctorDecisionOutcome,
    HandleDoctorDecisionService,
)
from triage_automation.config.settings import load_settings
from triage_automation.infrastructure.db.audit_repository import SqlAlchemyAuditRepository
from triage_automation.infrastructure.db.case_repository import SqlAlchemyCaseRepository
from triage_automation.infrastructure.db.job_queue_repository import SqlAlchemyJobQueueRepository
from triage_automation.infrastructure.db.session import create_session_factory
from triage_automation.infrastructure.http.hmac_auth import verify_hmac_signature


def build_decision_service(database_url: str) -> HandleDoctorDecisionService:
    """Build decision handling service with SQLAlchemy-backed dependencies."""

    session_factory = create_session_factory(database_url)
    return HandleDoctorDecisionService(
        case_repository=SqlAlchemyCaseRepository(session_factory),
        audit_repository=SqlAlchemyAuditRepository(session_factory),
        job_queue=SqlAlchemyJobQueueRepository(session_factory),
    )


def create_app(
    *,
    webhook_hmac_secret: str | None = None,
    decision_service: HandleDoctorDecisionService | None = None,
) -> FastAPI:
    """Create FastAPI app for authenticated doctor triage webhook callbacks."""

    if webhook_hmac_secret is None or decision_service is None:
        settings = load_settings()
        if webhook_hmac_secret is None:
            webhook_hmac_secret = settings.webhook_hmac_secret
        if decision_service is None:
            decision_service = build_decision_service(settings.database_url)

    assert decision_service is not None
    assert webhook_hmac_secret is not None

    app = FastAPI()

    @app.post(
        "/callbacks/triage-decision",
        response_model=TriageDecisionWebhookResponse,
    )
    async def triage_decision_callback(request: Request) -> TriageDecisionWebhookResponse:
        raw_body = await request.body()
        signature = request.headers.get("x-signature")

        if not verify_hmac_signature(
            secret=webhook_hmac_secret,
            body=raw_body,
            provided_signature=signature,
        ):
            raise HTTPException(status_code=401, detail="invalid signature")

        try:
            payload = TriageDecisionWebhookPayload.model_validate_json(raw_body)
        except ValidationError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        result = await decision_service.handle(payload)

        if result.outcome is HandleDoctorDecisionOutcome.NOT_FOUND:
            raise HTTPException(status_code=404, detail="case not found")

        if result.outcome is HandleDoctorDecisionOutcome.WRONG_STATE:
            raise HTTPException(status_code=409, detail="case not in WAIT_DOCTOR")

        return TriageDecisionWebhookResponse(ok=True)

    return app


def main() -> None:
    """Load configuration for bot-api process startup validation."""

    load_settings()


if __name__ == "__main__":
    main()
