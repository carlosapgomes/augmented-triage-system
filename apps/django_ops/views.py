"""Views for the django_ops operations web application.

Provides login/logout authentication, role-based redirect after login,
minimal placeholder landing pages for each operational role, PWA
installability assets (manifest and online-only service worker),
NIR PDF upload for case creation via web, NIR case listing dashboard,
NIR case detail with operational progress and timeline,
and doctor decision form for web-based medical decision submission.
"""

from pathlib import Path
from uuid import UUID

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.django_ops.models import Role

# Roles eligible for the installable PWA shell (remote-capable).
PWA_CAPABLE_ROLES: frozenset[str] = frozenset({"doctor", "manager", "admin"})

# Directory containing PWA static assets served directly by Django views.
PWA_STATIC_DIR: Path = Path(__file__).resolve().parent / "static" / "django_ops" / "pwa"

# Map each role value to its landing URL path.
ROLE_HOME_MAP: dict[str, str] = {
    "nir": "/nir/",
    "doctor": "/doctor/",
    "scheduler": "/scheduler/",
    "manager": "/manager/",
    "admin": "/admin/",
}


def _get_role_redirect_url(role: str) -> str:
    """Return the landing URL for the given role.

    Args:
        role: The user's role string value.

    Returns:
        The URL path for the role's landing page, defaults to ``/nir/``.
    """
    return ROLE_HOME_MAP.get(role, "/nir/")


def login_view(request: HttpRequest) -> HttpResponse:
    """Handle login form display and authentication.

    GET: renders the login form with email and password fields.
    POST: authenticates credentials and creates a session, then
    redirects to the role-specific landing page.

    Args:
        request: The HTTP request.

    Returns:
        The login form on GET/failed auth, or a redirect on success.
    """
    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            redirect_url = _get_role_redirect_url(str(user.role))
            return HttpResponseRedirect(redirect_url)
        return render(
            request,
            "django_ops/login.html",
            {"error": "Invalid email or password."},
        )

    return render(request, "django_ops/login.html")


@require_POST  # type: ignore[untyped-decorator]
def logout_view(request: HttpRequest) -> HttpResponse:
    """Log out the current user via POST and redirect to the login page.

    Args:
        request: The HTTP request.

    Returns:
        A redirect to the login page.
    """
    logout(request)
    return redirect("/login/")


@require_GET  # type: ignore[untyped-decorator]
def root_redirect(request: HttpRequest) -> HttpResponse:
    """Redirect unauthenticated users to login, authenticated to their home.

    Args:
        request: The HTTP request.

    Returns:
        A redirect to login (unauthenticated) or role home (authenticated).
    """
    if request.user.is_authenticated:
        redirect_url = _get_role_redirect_url(str(request.user.role))
        return HttpResponseRedirect(redirect_url)
    return redirect("/login/")


def _role_home(request: HttpRequest, role_label: str) -> HttpResponse:
    """Render a minimal placeholder page for a given role.

    For remote-capable roles (doctor, manager, admin) the response
    includes PWA installability metadata so the page is installable
    as a standalone app on supported mobile browsers.

    Args:
        request: The HTTP request.
        role_label: The display label for the role.

    Returns:
        An HTML response with the placeholder content.
    """
    user_role: str = getattr(request.user, "role", "")
    pwa_capable: bool = user_role in PWA_CAPABLE_ROLES
    return render(
        request,
        "django_ops/role_home.html",
        {
            "role_label": role_label,
            "pwa_capable": pwa_capable,
        },
    )


@login_required  # type: ignore[untyped-decorator]
@require_GET  # type: ignore[untyped-decorator]
def nir_home(request: HttpRequest) -> HttpResponse:
    """NIR dashboard listing active cases with operational progress.

    Shows non-cleaned cases ordered by latest activity descending.
    Only accessible to authenticated ``nir`` role users.
    Other roles receive a 403 Forbidden response.
    """
    if request.user.role != "nir":
        return HttpResponse("Access denied: NIR role required.", status=403)

    from apps.django_ops.service_wiring import build_nir_dashboard_service, run_async

    service = build_nir_dashboard_service()
    cases = run_async(service.list_nir_cases())

    return render(
        request,
        "django_ops/nir_dashboard.html",
        {
            "cases": cases,
            "user_email": request.user.email,
        },
    )


@login_required  # type: ignore[untyped-decorator]
@require_GET  # type: ignore[untyped-decorator]
def nir_case_detail(request: HttpRequest, case_id: UUID) -> HttpResponse:
    """NIR case detail with progress stepper and timeline.

    Shows operational progress, timeline events, and current status
    for a specific case. Only accessible to authenticated ``nir`` role
    users. Other roles receive 403 Forbidden.
    Returns 404 if the case does not exist.
    """
    if request.user.role != "nir":
        return HttpResponse("Access denied: NIR role required.", status=403)

    from apps.django_ops.service_wiring import build_nir_dashboard_service, run_async

    service = build_nir_dashboard_service()
    detail = run_async(service.get_case_detail(case_id=case_id))

    if detail is None:
        return HttpResponse("Case not found.", status=404)

    return render(
        request,
        "django_ops/nir_case_detail.html",
        {
            "detail": detail,
            "user_email": request.user.email,
        },
    )


@login_required  # type: ignore[untyped-decorator]
@require_GET  # type: ignore[untyped-decorator]
def doctor_home(request: HttpRequest) -> HttpResponse:
    """Doctor queue showing cases awaiting medical decision.

    Shows only cases in ``WAIT_DOCTOR`` status with clinical summaries.
    Only accessible to authenticated ``doctor`` role users.
    Other roles receive a 403 Forbidden response.
    """
    if request.user.role != "doctor":
        return HttpResponse("Access denied: Doctor role required.", status=403)

    from apps.django_ops.service_wiring import build_doctor_queue_service, run_async

    service = build_doctor_queue_service()
    cases = run_async(service.list_pending_cases())

    return render(
        request,
        "django_ops/doctor_queue.html",
        {
            "cases": cases,
            "user_email": request.user.email,
        },
    )


@login_required  # type: ignore[untyped-decorator]
@require_GET  # type: ignore[untyped-decorator]
def doctor_decision_form(request: HttpRequest, case_id: UUID) -> HttpResponse:
    """Render the doctor decision form for a given case.

    Only accessible to authenticated ``doctor`` role users.
    Shows case details and the structured decision form.
    Other roles receive a 403 Forbidden response.
    Returns 404 if the case does not exist or is not in WAIT_DOCTOR.
    """
    if request.user.role != "doctor":
        return HttpResponse("Access denied: Doctor role required.", status=403)

    from apps.django_ops.service_wiring import (
        build_handle_doctor_decision_service,
        run_async,
    )

    service = build_handle_doctor_decision_service()
    raw = run_async(service.get_form_case(case_id=case_id))
    from triage_automation.application.services.handle_doctor_decision_service import (
        DoctorFormCase,
    )
    form_case: DoctorFormCase | None = raw if isinstance(raw, DoctorFormCase) else None

    if form_case is None:
        return HttpResponse("Case not found or not awaiting decision.", status=404)

    return render(
        request,
        "django_ops/doctor_decision_form.html",
        {
            "case_id": str(case_id),
            "patient_name": form_case.patient_name,
            "patient_age": form_case.patient_age,
            "agency_record_number": form_case.agency_record_number,
            "user_email": request.user.email,
            "error_message": None,
        },
    )


@login_required  # type: ignore[untyped-decorator]
@require_POST  # type: ignore[untyped-decorator]
def doctor_decision_form_submit(
    request: HttpRequest, case_id: UUID
) -> HttpResponse:
    """Handle doctor decision form submission.

    Validates the form data, constructs a structured decision payload,
    and delegates to ``HandleDoctorDecisionService.handle_web`` for
    CAS update, audit persistence (including web human event), and
    next-step job enqueue.

    On success redirects to the doctor queue. On validation or
    processing failure, re-renders the form with an error message.
    """
    if request.user.role != "doctor":
        return HttpResponse("Access denied: Doctor role required.", status=403)

    from apps.django_ops.service_wiring import (
        build_handle_doctor_decision_service,
        run_async,
    )

    decision = request.POST.get("decision", "")
    support_flag = request.POST.get("support_flag", "none")
    admission_flow_raw = request.POST.get("admission_flow", "")
    reason = request.POST.get("reason", "")

    # ── Form-level validation ─────────────────────────────────────
    from triage_automation.application.dto.webhook_models import (
        AdmissionFlow,
    )

    error = _validate_decision_form(
        decision=decision,
        support_flag=support_flag,
        admission_flow_raw=admission_flow_raw,
        reason=reason,
    )
    if error:
        return _render_decision_form_error(
            request=request,
            case_id=case_id,
            error_message=error,
        )

    # ── Build payload and delegate ─────────────────────────────────
    from triage_automation.application.dto.webhook_models import (
        TriageDecisionWebhookPayload,
    )
    from triage_automation.application.services.handle_doctor_decision_service import (
        HandleDoctorDecisionOutcome,
    )

    admission_flow: AdmissionFlow | None = (
        admission_flow_raw if admission_flow_raw in ("scheduled", "immediate") else None
    )
    reason_value: str | None = reason if reason and reason.strip() else None

    payload = TriageDecisionWebhookPayload(
        case_id=case_id,
        doctor_user_id=str(request.user.pk),
        decision=decision,
        support_flag=support_flag,
        admission_flow=admission_flow,
        reason=reason_value,
    )

    service = build_handle_doctor_decision_service()

    raw_result = run_async(
        service.handle_web(payload, actor_email=request.user.email)
    )
    from triage_automation.application.services.handle_doctor_decision_service import (
        HandleDoctorDecisionResult,
    )
    assert isinstance(raw_result, HandleDoctorDecisionResult)
    result: HandleDoctorDecisionResult = raw_result

    if result.outcome != HandleDoctorDecisionOutcome.APPLIED:
        error_map: dict[HandleDoctorDecisionOutcome, str] = {
            HandleDoctorDecisionOutcome.NOT_FOUND: "Caso não encontrado.",
            HandleDoctorDecisionOutcome.WRONG_STATE: (
                "O caso não está aguardando decisão médica."
            ),
            HandleDoctorDecisionOutcome.DUPLICATE_OR_RACE: (
                "Decisão já aplicada ou conflito detectado."
            ),
        }
        return _render_decision_form_error(
            request=request,
            case_id=case_id,
            error_message=error_map.get(
                result.outcome, "Erro ao processar decisão."
            ),
        )

    return HttpResponseRedirect("/doctor/")


def _validate_decision_form(
    *,
    decision: str,
    support_flag: str,
    admission_flow_raw: str,
    reason: str,
) -> str | None:
    """Validate form data for the doctor decision form.

    Returns an error message string if validation fails, or None if valid.
    """
    if decision not in ("accept", "deny"):
        return "Decisão inválida. Use 'accept' ou 'deny'."

    if decision == "deny":
        if not reason or not reason.strip():
            return "É obrigatório informar o motivo da negativa."
        if support_flag not in ("", "none"):
            return "support_flag deve ser 'none' para decisão deny."
        # No admission_flow for deny
        return None

    # decision == "accept"
    if not admission_flow_raw or admission_flow_raw not in (
        "scheduled",
        "immediate",
    ):
        return (
            "Fluxo de admissão inválido. "
            "Use 'scheduled' ou 'immediate'."
        )

    # Validate support_flag for accept
    if support_flag not in ("", "none", "anesthesist", "anesthesist_icu"):
        return "Support flag inválido."

    return None


def _validate_scheduler_confirmation_form(
    request: HttpRequest,
) -> str | None:
    """Validate form data for the scheduler confirmation/denial form.

    Returns an error message string if validation fails, or None if valid.
    """
    action = request.POST.get("action", "")
    if action not in ("confirm", "deny"):
        return "Ação inválida. Use 'confirm' ou 'deny'."

    if action == "deny":
        deny_reason = request.POST.get("deny_reason", "")
        if not deny_reason or not deny_reason.strip():
            return "É obrigatório informar o motivo da negativa."
        return None

    # action == "confirm"
    appointment_date = request.POST.get("appointment_date", "")
    appointment_time = request.POST.get("appointment_time", "")
    location = request.POST.get("location", "")

    if not appointment_date or not appointment_date.strip():
        return "É obrigatório informar a data do agendamento."
    if not appointment_time or not appointment_time.strip():
        return "É obrigatório informar o horário do agendamento."
    if not location or not location.strip():
        return "É obrigatório informar o local do agendamento."

    # Validate date/time format
    from datetime import datetime
    try:
        datetime.strptime(
            f"{appointment_date.strip()} {appointment_time.strip()}",
            "%d/%m/%Y %H:%M",
        )
    except ValueError:
        return (
            "Data/hora inválida."
            " Use o formato DD/MM/AAAA para data e HH:MM para horário."
        )

    return None


def _render_scheduler_confirmation_form_error(
    *,
    request: HttpRequest,
    case_id: UUID,
    error_message: str,
) -> HttpResponse:
    """Re-render the scheduler confirmation form with an error message.

    Loads case details via the public service API to populate the form
    context alongside the error.
    """
    from apps.django_ops.service_wiring import (
        build_handle_scheduler_confirmation_service,
        run_async,
    )

    service = build_handle_scheduler_confirmation_service()
    raw = run_async(service.get_form_case(case_id=case_id))
    from triage_automation.application.services.handle_scheduler_confirmation_service import (
        SchedulerFormCase,
    )
    form_case: SchedulerFormCase | None = (
        raw if isinstance(raw, SchedulerFormCase) else None
    )

    patient_name: str | None = None
    patient_age: int | None = None
    agency_record_number: str | None = None
    if form_case is not None:
        agency_record_number = form_case.agency_record_number
        patient_name = form_case.patient_name
        patient_age = form_case.patient_age

    return render(
        request,
        "django_ops/scheduler_confirmation_form.html",
        {
            "case_id": str(case_id),
            "patient_name": patient_name,
            "patient_age": patient_age,
            "agency_record_number": agency_record_number,
            "user_email": request.user.email,
            "error_message": error_message,
        },
    )


def _render_decision_form_error(
    *,
    request: HttpRequest,
    case_id: UUID,
    error_message: str,
) -> HttpResponse:
    """Re-render the decision form with an error message.

    Loads case details via the public service API to populate the form
    context alongside the error.
    """
    from apps.django_ops.service_wiring import (
        build_handle_doctor_decision_service,
        run_async,
    )

    service = build_handle_doctor_decision_service()
    raw = run_async(service.get_form_case(case_id=case_id))
    from triage_automation.application.services.handle_doctor_decision_service import (
        DoctorFormCase,
    )
    form_case: DoctorFormCase | None = raw if isinstance(raw, DoctorFormCase) else None

    patient_name: str | None = None
    patient_age: int | None = None
    agency_record_number: str | None = None
    if form_case is not None:
        agency_record_number = form_case.agency_record_number
        patient_name = form_case.patient_name
        patient_age = form_case.patient_age

    return render(
        request,
        "django_ops/doctor_decision_form.html",
        {
            "case_id": str(case_id),
            "patient_name": patient_name,
            "patient_age": patient_age,
            "agency_record_number": agency_record_number,
            "user_email": request.user.email,
            "error_message": error_message,
        },
    )


@login_required  # type: ignore[untyped-decorator]
@require_GET  # type: ignore[untyped-decorator]
def scheduler_home(request: HttpRequest) -> HttpResponse:
    """Scheduler queue showing cases awaiting scheduling confirmation.

    Shows only cases in ``WAIT_APPT`` status with clinical summaries.
    Only accessible to authenticated ``scheduler`` role users.
    Other roles receive a 403 Forbidden response.
    """
    if request.user.role != "scheduler":
        return HttpResponse("Access denied: Scheduler role required.", status=403)

    from apps.django_ops.service_wiring import build_scheduler_queue_service, run_async

    service = build_scheduler_queue_service()
    cases = run_async(service.list_pending_cases())

    return render(
        request,
        "django_ops/scheduler_queue.html",
        {
            "cases": cases,
            "user_email": request.user.email,
        },
    )


@login_required  # type: ignore[untyped-decorator]
@require_GET  # type: ignore[untyped-decorator]
def scheduler_confirmation_form(
    request: HttpRequest, case_id: UUID
) -> HttpResponse:
    """Render the scheduler confirmation/denial form for a given case.

    Only accessible to authenticated ``scheduler`` role users.
    Shows case details and the structured confirmation/denial form.
    Other roles receive a 403 Forbidden response.
    Returns 404 if the case does not exist or is not in WAIT_APPT.
    """
    if request.user.role != "scheduler":
        return HttpResponse("Access denied: Scheduler role required.", status=403)

    from apps.django_ops.service_wiring import (
        build_handle_scheduler_confirmation_service,
        run_async,
    )

    service = build_handle_scheduler_confirmation_service()
    raw = run_async(service.get_form_case(case_id=case_id))
    from triage_automation.application.services.handle_scheduler_confirmation_service import (
        SchedulerFormCase,
    )
    form_case: SchedulerFormCase | None = (
        raw if isinstance(raw, SchedulerFormCase) else None
    )

    if form_case is None:
        return HttpResponse(
            "Case not found or not awaiting scheduling confirmation.",
            status=404,
        )

    return render(
        request,
        "django_ops/scheduler_confirmation_form.html",
        {
            "case_id": str(case_id),
            "patient_name": form_case.patient_name,
            "patient_age": form_case.patient_age,
            "agency_record_number": form_case.agency_record_number,
            "user_email": request.user.email,
            "error_message": None,
        },
    )


@login_required  # type: ignore[untyped-decorator]
@require_POST  # type: ignore[untyped-decorator]
def scheduler_confirmation_form_submit(
    request: HttpRequest, case_id: UUID
) -> HttpResponse:
    """Handle scheduler confirmation/denial form submission.

    Validates the form data, constructs a payload, and delegates to
    ``HandleSchedulerConfirmationService`` for CAS update, audit
    persistence, and next-step job enqueue.

    On success, persists a web human event audit entry and redirects
    to the scheduler queue. On validation or processing failure,
    re-renders the form with an error message.
    """
    if request.user.role != "scheduler":
        return HttpResponse("Access denied: Scheduler role required.", status=403)

    from apps.django_ops.service_wiring import (
        build_handle_scheduler_confirmation_service,
        run_async,
    )

    action = request.POST.get("action", "")

    # ── Form-level validation ────────────────────────────────────
    error = _validate_scheduler_confirmation_form(request)
    if error:
        return _render_scheduler_confirmation_form_error(
            request=request,
            case_id=case_id,
            error_message=error,
        )

    # ── Build payload and delegate ───────────────────────────────
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from triage_automation.application.services.handle_scheduler_confirmation_service import (
        HandleSchedulerConfirmationOutcome,
        HandleSchedulerConfirmationResult,
        SchedulerConfirmationPayload,
    )

    if action == "confirm":
        appointment_date = request.POST.get("appointment_date", "")
        appointment_time = request.POST.get("appointment_time", "")
        appointment_location = request.POST.get("location", "")
        appointment_instructions = request.POST.get("instructions", "") or None

        brt = ZoneInfo("America/Bahia")
        naive = datetime.strptime(
            f"{appointment_date} {appointment_time}",
            "%d/%m/%Y %H:%M",
        )
        appointment_at = naive.replace(tzinfo=brt)

        payload = SchedulerConfirmationPayload(
            case_id=case_id,
            scheduler_user_id=str(request.user.pk),
            appointment_status="confirmed",
            appointment_at=appointment_at,
            appointment_location=appointment_location or None,
            appointment_instructions=appointment_instructions,
            appointment_reason=None,
        )
    else:
        deny_reason = request.POST.get("deny_reason", "")
        payload = SchedulerConfirmationPayload(
            case_id=case_id,
            scheduler_user_id=str(request.user.pk),
            appointment_status="denied",
            appointment_at=None,
            appointment_location=None,
            appointment_instructions=None,
            appointment_reason=deny_reason or None,
        )

    service = build_handle_scheduler_confirmation_service()

    raw_result = run_async(
        service.handle_web(payload, actor_email=request.user.email)
    )
    assert isinstance(raw_result, HandleSchedulerConfirmationResult)
    result: HandleSchedulerConfirmationResult = raw_result

    if result.outcome != HandleSchedulerConfirmationOutcome.APPLIED:
        error_map: dict[HandleSchedulerConfirmationOutcome, str] = {
            HandleSchedulerConfirmationOutcome.NOT_FOUND: (
                "Caso não encontrado."
            ),
            HandleSchedulerConfirmationOutcome.WRONG_STATE: (
                "O caso não está aguardando confirmação de agendamento."
            ),
            HandleSchedulerConfirmationOutcome.DUPLICATE_OR_RACE: (
                "Confirmação já aplicada ou conflito detectado."
            ),
        }
        return _render_scheduler_confirmation_form_error(
            request=request,
            case_id=case_id,
            error_message=error_map.get(
                result.outcome, "Erro ao processar confirmação."
            ),
        )

    return HttpResponseRedirect("/scheduler/")


@login_required  # type: ignore[untyped-decorator]
@require_POST  # type: ignore[untyped-decorator]
def nir_case_acknowledge_submit(
    request: HttpRequest, case_id: UUID
) -> HttpResponse:
    """Handle NIR final acknowledgment submission.

    Processes the confirmation of receipt for the final case result.
    Uses ``NirFinalAcknowledgmentService.acknowledge`` to call
    ``claim_cleanup_trigger_if_first`` (idempotent CAS), persist
    a web human audit event, and enqueue the ``execute_cleanup`` job.

    On success, redirects to the NIR dashboard. On validation or
    processing failure, redirects to the case detail page.

    This replaces the Room-1 Matrix thumbs-up reaction as the
    canonical human closure checkpoint.
    """
    if request.user.role != "nir":
        return HttpResponse("Access denied: NIR role required.", status=403)

    from apps.django_ops.service_wiring import (
        build_nir_final_acknowledgment_service,
        run_async,
    )
    from triage_automation.application.services.nir_final_acknowledgment_service import (
        NirFinalAcknowledgmentOutcome,
        NirFinalAcknowledgmentResult,
    )

    service = build_nir_final_acknowledgment_service()

    raw_result = run_async(
        service.acknowledge(
            case_id=case_id,
            nir_user_id=str(request.user.pk),
            actor_email=request.user.email,
        )
    )
    assert isinstance(raw_result, NirFinalAcknowledgmentResult)
    result: NirFinalAcknowledgmentResult = raw_result

    if result.outcome == NirFinalAcknowledgmentOutcome.APPLIED:
        return HttpResponseRedirect("/nir/")

    if result.outcome == NirFinalAcknowledgmentOutcome.NOT_FOUND:
        return HttpResponse("Caso não encontrado.", status=404)

    # WRONG_STATE or DUPLICATE_OR_RACE: redirect to case detail
    # with the result still visible (duplicate is harmless).
    return HttpResponseRedirect(f"/nir/cases/{case_id}/")


@login_required  # type: ignore[untyped-decorator]
@require_GET  # type: ignore[untyped-decorator]
def manager_home(request: HttpRequest) -> HttpResponse:
    """Manager dashboard showing consolidated operational case listing.

    Shows all cases with filters, pagination, and operational totals.
    Accessible to authenticated ``manager`` and ``admin`` role users.
    Other roles receive a 403 Forbidden response.
    """
    if request.user.role not in ("manager", "admin"):
        return HttpResponse(
            "Access denied: Manager or Admin role required.", status=403
        )

    from datetime import date, datetime

    from apps.django_ops.service_wiring import build_manager_dashboard_service, run_async
    from triage_automation.domain.case_status import CaseStatus

    # Parse query parameters
    page_str = request.GET.get("page", "1")
    try:
        page = int(page_str)
    except ValueError:
        page = 1
    if page < 1:
        page = 1

    page_size_str = request.GET.get("page_size", "25")
    try:
        page_size = int(page_size_str)
    except ValueError:
        page_size = 25
    if page_size < 1:
        page_size = 25

    status_str = request.GET.get("status", "")
    status_filter: CaseStatus | None = None
    if status_str:
        try:
            status_filter = CaseStatus(status_str)
        except ValueError:
            pass

    from_date_str = request.GET.get("from_date", "")
    from_date: date | None = None
    if from_date_str:
        try:
            from_date = datetime.strptime(from_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    to_date_str = request.GET.get("to_date", "")
    to_date: date | None = None
    if to_date_str:
        try:
            to_date = datetime.strptime(to_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    service = build_manager_dashboard_service()
    raw_dashboard = run_async(
        service.list_cases(
            page=page,
            page_size=page_size,
            status=status_filter,
            from_date=from_date,
            to_date=to_date,
            tz_offset_minutes=-180,
        )
    )
    from triage_automation.application.services.manager_dashboard_service import (
        ManagerDashboardPage,
    )
    assert isinstance(raw_dashboard, ManagerDashboardPage)
    dashboard: ManagerDashboardPage = raw_dashboard

    total_cases = dashboard.total
    total_pages = (
        max(1, (total_cases + page_size - 1) // page_size)
        if total_cases > 0
        else 1
    )
    has_next = page < total_pages
    has_prev = page > 1

    return render(
        request,
        "django_ops/manager_dashboard.html",
        {
            "cases": dashboard.cases,
            "page": dashboard.page,
            "page_size": dashboard.page_size,
            "total": dashboard.total,
            "totals": dashboard.totals,
            "user_email": request.user.email,
            "status_filter": status_str,
            "from_date": from_date_str,
            "to_date": to_date_str,
            "has_prev": has_prev,
            "has_next": has_next,
            "prev_page": page - 1,
            "next_page": page + 1,
        },
    )


@login_required  # type: ignore[untyped-decorator]
@require_GET  # type: ignore[untyped-decorator]
def manager_case_detail(request: HttpRequest, case_id: UUID) -> HttpResponse:
    """Manager case detail with audit timeline and operational summary.

    Shows the full case detail including chronological timeline events,
    operational summary, and current status. Accessible to authenticated
    ``manager`` and ``admin`` role users. Other roles receive 403 Forbidden.
    Returns 404 if the case does not exist.

    The view is intentionally read-only — no mutation or acknowledgment
    controls are exposed.
    """
    if request.user.role not in ("manager", "admin"):
        return HttpResponse(
            "Access denied: Manager or Admin role required.", status=403
        )

    from apps.django_ops.service_wiring import build_manager_dashboard_service, run_async

    service = build_manager_dashboard_service()
    detail = run_async(service.get_case_detail(case_id=case_id))

    if detail is None:
        return HttpResponse("Case not found.", status=404)

    return render(
        request,
        "django_ops/manager_case_detail.html",
        {
            "detail": detail,
            "user_email": request.user.email,
        },
    )


@login_required  # type: ignore[untyped-decorator]
@require_GET  # type: ignore[untyped-decorator]
def admin_home(request: HttpRequest) -> HttpResponse:
    """Admin system console landing page.

    Shows the consolidated operational dashboard with admin navigation
    links (users, prompts). Only accessible to authenticated ``admin``
    role users. Other roles receive 403 Forbidden.

    ``manager`` users should use ``/manager/`` for read-only supervisory
    dashboard access.
    """
    if request.user.role != "admin":
        return HttpResponse("Access denied: Admin role required.", status=403)

    return manager_home(request)


@login_required  # type: ignore[untyped-decorator]
def admin_users_home(request: HttpRequest) -> HttpResponse:
    """Admin user-management page and create-user action.

    GET: renders the user listing with create/role-change forms.
    POST: creates a new user via the application-layer service.
    """
    if request.user.role != "admin":
        return HttpResponse("Access denied: Admin role required.", status=403)

    from apps.django_ops.service_wiring import build_django_user_management_service
    from triage_automation.application.ports.django_user_store_port import (
        DjangoCreateUserRequest,
    )
    from triage_automation.application.services.django_user_management import (
        DjangoActor,
        DjangoEmailAlreadyExistsError,
        DjangoInvalidEmailError,
        DjangoInvalidPasswordError,
        DjangoInvalidRoleError,
        DjangoUserManagementAuthorizationError,
    )

    if request.method == "POST":
        email = request.POST.get("email", "")
        password = request.POST.get("password", "")
        role_value = request.POST.get("role", "")

        actor = DjangoActor(
            pk=request.user.pk,
            email=request.user.email,
            role=request.user.role,
        )
        service = build_django_user_management_service()
        try:
            created = service.create_user(
                actor=actor,
                payload=DjangoCreateUserRequest(
                    email=email,
                    password=password,
                    role=role_value,
                ),
            )
        except DjangoInvalidRoleError:
            return HttpResponseRedirect(
                "/admin/users/?error=Perfil+de+usuario+invalido."
            )
        except DjangoInvalidEmailError:
            return HttpResponseRedirect(
                "/admin/users/?error=Email+nao+pode+ficar+vazio."
            )
        except DjangoInvalidPasswordError:
            return HttpResponseRedirect(
                "/admin/users/?error=Senha+nao+pode+ficar+vazia."
            )
        except DjangoEmailAlreadyExistsError:
            return HttpResponseRedirect(
                "/admin/users/?error=Email+ja+cadastrado."
            )
        except DjangoUserManagementAuthorizationError:
            return HttpResponse(
                "Access denied: Admin role required.", status=403
            )

        return HttpResponseRedirect(f"/admin/users/?created_email={created.email}")

    service = build_django_user_management_service()
    user_items = service.list_users()
    return render(
        request,
        "django_ops/admin_users.html",
        {
            "users": user_items,
            "supported_roles": [choice for choice, _ in Role.choices],
            "error_message": request.GET.get("error"),
            "created_email": request.GET.get("created_email"),
            "updated_email": request.GET.get("updated_email"),
        },
    )


@login_required  # type: ignore[untyped-decorator]
@require_POST  # type: ignore[untyped-decorator]
def admin_user_role_update(request: HttpRequest, user_id: int) -> HttpResponse:
    """Admin role-change action for an existing user account."""
    if request.user.role != "admin":
        return HttpResponse("Access denied: Admin role required.", status=403)

    from apps.django_ops.service_wiring import build_django_user_management_service
    from triage_automation.application.services.django_user_management import (
        DjangoActor,
        DjangoInvalidRoleError,
        DjangoLastActiveAdminError,
        DjangoUserManagementAuthorizationError,
        DjangoUserNotFoundError,
    )

    role_value = request.POST.get("role", "")
    actor = DjangoActor(
        pk=request.user.pk,
        email=request.user.email,
        role=request.user.role,
    )
    service = build_django_user_management_service()
    try:
        updated = service.update_user_role(
            actor=actor,
            target_pk=user_id,
            new_role=role_value,
        )
    except DjangoInvalidRoleError:
        return HttpResponseRedirect(
            "/admin/users/?error=Perfil+de+usuario+invalido."
        )
    except DjangoUserNotFoundError:
        return HttpResponseRedirect(
            "/admin/users/?error=Usuario+alvo+nao+encontrado."
        )
    except DjangoLastActiveAdminError:
        return HttpResponseRedirect(
            "/admin/users/?error=Pelo+menos+um+admin+ativo+deve+permanecer."
        )
    except DjangoUserManagementAuthorizationError:
        return HttpResponse(
            "Access denied: Admin role required.", status=403
        )

    return HttpResponseRedirect(f"/admin/users/?updated_email={updated.email}")


@login_required  # type: ignore[untyped-decorator]
@require_POST  # type: ignore[untyped-decorator]
def admin_user_block(request: HttpRequest, user_id: int) -> HttpResponse:
    """Admin block action for an existing user account."""
    if request.user.role != "admin":
        return HttpResponse("Access denied: Admin role required.", status=403)

    from apps.django_ops.service_wiring import build_django_user_management_service
    from triage_automation.application.services.django_user_management import (
        DjangoActor,
        DjangoLastActiveAdminError,
        DjangoSelfUserManagementError,
        DjangoUserManagementAuthorizationError,
        DjangoUserNotFoundError,
    )

    actor = DjangoActor(
        pk=request.user.pk,
        email=request.user.email,
        role=request.user.role,
    )
    service = build_django_user_management_service()
    try:
        service.block_user(actor=actor, target_pk=user_id)
    except DjangoUserNotFoundError:
        return HttpResponseRedirect(
            "/admin/users/?error=Usuario+alvo+nao+encontrado."
        )
    except DjangoSelfUserManagementError:
        return HttpResponseRedirect(
            "/admin/users/?error=Nao+e+permitido+bloquear+a+propria+conta."
        )
    except DjangoLastActiveAdminError:
        return HttpResponseRedirect(
            "/admin/users/?error=Pelo+menos+um+admin+ativo+deve+permanecer."
        )
    except DjangoUserManagementAuthorizationError:
        return HttpResponse(
            "Access denied: Admin role required.", status=403
        )

    return HttpResponseRedirect("/admin/users/")


@login_required  # type: ignore[untyped-decorator]
@require_POST  # type: ignore[untyped-decorator]
def admin_user_activate(request: HttpRequest, user_id: int) -> HttpResponse:
    """Admin activate/reactivate action for an existing user account."""
    if request.user.role != "admin":
        return HttpResponse("Access denied: Admin role required.", status=403)

    from apps.django_ops.service_wiring import build_django_user_management_service
    from triage_automation.application.services.django_user_management import (
        DjangoActor,
        DjangoUserManagementAuthorizationError,
        DjangoUserNotFoundError,
    )

    actor = DjangoActor(
        pk=request.user.pk,
        email=request.user.email,
        role=request.user.role,
    )
    service = build_django_user_management_service()
    try:
        service.activate_user(actor=actor, target_pk=user_id)
    except DjangoUserNotFoundError:
        return HttpResponseRedirect(
            "/admin/users/?error=Usuario+alvo+nao+encontrado."
        )
    except DjangoUserManagementAuthorizationError:
        return HttpResponse(
            "Access denied: Admin role required.", status=403
        )

    return HttpResponseRedirect("/admin/users/")


@login_required  # type: ignore[untyped-decorator]
def admin_prompts_home(request: HttpRequest) -> HttpResponse:
    """Admin prompt management page — consolidated Django surface.

    GET: renders prompt names, versions, active state, and
    activation controls for each prompt.

    Only accessible to authenticated ``admin`` role users.
    Other roles receive 403 Forbidden.
    """
    if request.user.role != "admin":
        return HttpResponse("Access denied: Admin role required.", status=403)

    from apps.django_ops.service_wiring import (
        build_django_prompt_management_service,
        run_async,
    )

    service = build_django_prompt_management_service()
    items = run_async(service.list_versions())
    from triage_automation.application.ports.prompt_management_repository_port import (
        PromptVersionRecord,
    )
    assert isinstance(items, list)
    typed_items: list[PromptVersionRecord] = items

    # Group versions by prompt name.
    prompts_by_name: dict[str, list[PromptVersionRecord]] = {}
    for item in typed_items:
        prompts_by_name.setdefault(item.name, []).append(item)

    # Sort names for deterministic rendering.
    sorted_names = sorted(prompts_by_name.keys())

    return render(
        request,
        "django_ops/admin_prompts.html",
        {
            "prompts_by_name": {name: prompts_by_name[name] for name in sorted_names},
            "prompt_visible_limit": 8,
            "activated_name": request.GET.get("activated_name", ""),
            "activated_version": request.GET.get("activated_version", ""),
            "created_name": request.GET.get("created_name", ""),
            "created_version": request.GET.get("created_version", ""),
            "error_message": request.GET.get("error", ""),
        },
    )


@login_required  # type: ignore[untyped-decorator]
def admin_prompt_version_detail(
    request: HttpRequest, prompt_name: str, version: int
) -> HttpResponse:
    """Render one prompt version with immutable content and create-new-version form.

    Only accessible to authenticated ``admin`` role users.
    Other roles receive 403 Forbidden.
    Returns a redirect to the prompt list if version not found.
    """
    if request.user.role != "admin":
        return HttpResponse("Access denied: Admin role required.", status=403)

    from urllib.parse import urlencode

    from apps.django_ops.service_wiring import (
        build_django_prompt_management_service,
        run_async,
    )

    service = build_django_prompt_management_service()
    item = run_async(
        service.get_version(prompt_name=prompt_name, version=version)
    )
    from triage_automation.application.ports.prompt_management_repository_port import (
        PromptVersionContentRecord,
    )

    if item is None or not isinstance(item, PromptVersionContentRecord):
        return HttpResponseRedirect(
            f"/admin/prompts/?{urlencode({'error': 'Versao de prompt nao encontrada.'})}"
        )

    return render(
        request,
        "django_ops/admin_prompt_version_detail.html",
        {
            "prompt_name": item.name,
            "version": item.version,
            "is_active": item.is_active,
            "content": item.content,
            "error_message": request.GET.get("error", ""),
        },
    )


@login_required  # type: ignore[untyped-decorator]
@require_POST  # type: ignore[untyped-decorator]
def admin_prompt_activate(
    request: HttpRequest, prompt_name: str
) -> HttpResponse:
    """Activate a prompt version from the server-rendered admin page.

    Only accessible to authenticated ``admin`` role users.
    Redirects to prompt list with success/error query params.
    """
    if request.user.role != "admin":
        return HttpResponse("Access denied: Admin role required.", status=403)

    from urllib.parse import urlencode

    from apps.django_ops.django_prompt_management import (
        DjangoPromptVersionNotFoundError,
    )
    from apps.django_ops.service_wiring import (
        build_django_prompt_management_service,
        run_async,
    )

    version_str = request.POST.get("version", "").strip()
    if not version_str or not version_str.isdigit():
        return HttpResponseRedirect(
            f"/admin/prompts/?{urlencode({'error': 'Versao invalida.'})}"
        )
    version = int(version_str)
    if version <= 0:
        return HttpResponseRedirect(
            f"/admin/prompts/?{urlencode({'error': 'Versao invalida.'})}"
        )

    service = build_django_prompt_management_service()
    try:
        activated = run_async(
            service.activate_version(
                prompt_name=prompt_name,
                version=version,
                actor_pk=request.user.pk,
                actor_email=request.user.email,
            )
        )
    except DjangoPromptVersionNotFoundError:
        return HttpResponseRedirect(
            f"/admin/prompts/?{urlencode({'error': 'Versao de prompt nao encontrada.'})}"
        )

    from triage_automation.application.ports.prompt_management_repository_port import (
        PromptVersionRecord,
    )
    assert isinstance(activated, PromptVersionRecord)

    query_string = urlencode(
        {
            "activated_name": activated.name,
            "activated_version": str(activated.version),
        }
    )
    return HttpResponseRedirect(f"/admin/prompts/?{query_string}")


@login_required  # type: ignore[untyped-decorator]
@require_POST  # type: ignore[untyped-decorator]
def admin_prompt_create(
    request: HttpRequest, prompt_name: str
) -> HttpResponse:
    """Create a new immutable prompt version from HTML form content.

    Only accessible to authenticated ``admin`` role users.
    Redirects to prompt list with success query params or back to
    version detail with error on invalid/missing content.
    """
    if request.user.role != "admin":
        return HttpResponse("Access denied: Admin role required.", status=403)

    from urllib.parse import urlencode

    from apps.django_ops.django_prompt_management import (
        DjangoPromptVersionNotFoundError,
    )
    from apps.django_ops.service_wiring import (
        build_django_prompt_management_service,
        run_async,
    )

    source_version_str = request.POST.get("source_version", "").strip()
    if not source_version_str or not source_version_str.isdigit():
        return HttpResponseRedirect(
            f"/admin/prompts/?{urlencode({'error': 'Versao de origem invalida.'})}"
        )
    source_version = int(source_version_str)
    if source_version <= 0:
        return HttpResponseRedirect(
            f"/admin/prompts/?{urlencode({'error': 'Versao de origem invalida.'})}"
        )

    content = request.POST.get("content", "").strip()
    if not content:
        return HttpResponseRedirect(
            f"/admin/prompts/{prompt_name}/versions/{source_version}/"
            f"?{urlencode({'error': 'Conteudo do prompt nao pode ficar vazio.'})}"
        )

    service = build_django_prompt_management_service()
    try:
        created = run_async(
            service.create_version(
                prompt_name=prompt_name,
                source_version=source_version,
                content=content,
                actor_pk=request.user.pk,
                actor_email=request.user.email,
            )
        )
    except DjangoPromptVersionNotFoundError:
        return HttpResponseRedirect(
            f"/admin/prompts/{prompt_name}/versions/{source_version}/"
            f"?{urlencode({'error': 'Versao de origem nao encontrada.'})}"
        )

    from triage_automation.application.ports.prompt_management_repository_port import (
        PromptVersionRecord,
    )
    assert isinstance(created, PromptVersionRecord)

    query_string = urlencode(
        {
            "created_name": created.name,
            "created_version": str(created.version),
        }
    )
    return HttpResponseRedirect(f"/admin/prompts/?{query_string}")


@require_GET  # type: ignore[untyped-decorator]
def manifest_view(request: HttpRequest) -> HttpResponse:
    """Serve the PWA web app manifest.

    Returns the manifest.webmanifest file with the correct
    ``application/manifest+json`` content type so browsers
    recognize it as a valid installability document.

    Args:
        request: The HTTP request.

    Returns:
        The manifest file content.
    """
    manifest_path = PWA_STATIC_DIR / "manifest.webmanifest"
    return HttpResponse(
        manifest_path.read_bytes(),
        content_type="application/manifest+json",
    )


@require_GET  # type: ignore[untyped-decorator]
def service_worker_view(request: HttpRequest) -> HttpResponse:
    """Serve the online-only PWA service worker.

    The service worker uses network-only fetch behavior and does
    not cache any clinical content for offline use.

    Args:
        request: The HTTP request.

    Returns:
        The service worker JavaScript content.
    """
    sw_path = PWA_STATIC_DIR / "service-worker.js"
    return HttpResponse(
        sw_path.read_bytes(),
        content_type="text/javascript",
    )


def smoke(request: HttpRequest) -> HttpResponse:
    """Health/smoke endpoint to validate Django app is running.

    Returns a JSON response with status ``ok`` so monitoring and
    deployment checks can confirm the app is healthy.
    """

    return JsonResponse({"status": "ok"})


@login_required  # type: ignore[untyped-decorator]
@require_GET  # type: ignore[untyped-decorator]
def nir_upload(request: HttpRequest) -> HttpResponse:
    """Render the NIR PDF upload form.

    Only accessible to authenticated ``nir`` role users.
    Other roles receive a 403 Forbidden response.
    """
    if request.user.role != "nir":
        return HttpResponse("Access denied: NIR role required.", status=403)
    return render(request, "django_ops/nir_upload.html", {"error_message": None})


@login_required  # type: ignore[untyped-decorator]
@require_POST  # type: ignore[untyped-decorator]
def nir_upload_submit(request: HttpRequest) -> HttpResponse:
    """Handle NIR PDF upload submission.

    Validates the uploaded file, creates a case via the shared
    application service, and renders the result page.

    On validation failure, re-renders the upload form with an error.
    On unexpected error, renders the result page with an error message.
    """
    if request.user.role != "nir":
        return HttpResponse("Access denied: NIR role required.", status=403)

    uploaded_file = request.FILES.get("pdf_file")

    if uploaded_file is None:
        return render(
            request,
            "django_ops/nir_upload.html",
            {"error_message": "Selecione um arquivo PDF para enviar."},
        )

    pdf_bytes = uploaded_file.read()
    filename = uploaded_file.name or ""
    content_type = uploaded_file.content_type or None

    user_id = str(request.user.pk)
    user_email = request.user.email

    from apps.django_ops.service_wiring import build_nir_web_intake_service, run_async
    from triage_automation.application.services.nir_web_intake_service import (
        NirWebIntakeResult,
        NirWebIntakeValidationError,
    )

    service = build_nir_web_intake_service()

    try:
        result: NirWebIntakeResult = run_async(  # type: ignore[assignment]
            service.ingest_web_pdf(
                pdf_bytes=pdf_bytes,
                filename=filename,
                content_type=content_type,
                uploaded_by_user_id=user_id,
                uploaded_by_email=user_email,
            )
        )
    except NirWebIntakeValidationError as exc:
        return render(
            request,
            "django_ops/nir_upload.html",
            {"error_message": str(exc)},
        )
    except Exception as exc:
        return render(
            request,
            "django_ops/nir_upload_result.html",
            {
                "case_id": "—",
                "status": "ERRO",
                "created_at": "—",
                "error_message": f"Erro ao criar caso: {exc}",
            },
        )

    if not result.processed:
        return render(
            request,
            "django_ops/nir_upload_result.html",
            {
                "case_id": "—",
                "status": "REJEITADO",
                "created_at": "—",
                "error_message": result.reason or "Upload rejeitado.",
            },
        )

    from django.utils import timezone as django_tz

    now = django_tz.now()
    return render(
        request,
        "django_ops/nir_upload_result.html",
        {
            "case_id": result.case_id,
            "status": "Recebido — processando",
            "created_at": now.strftime("%d/%m/%Y %H:%M"),
            "error_message": None,
        },
    )
