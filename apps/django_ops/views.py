"""Views for the django_ops operations web application.

Provides login/logout authentication, role-based redirect after login,
minimal placeholder landing pages for each operational role, PWA
installability assets (manifest and online-only service worker),
NIR PDF upload for case creation via web, NIR case listing dashboard,
and NIR case detail with operational progress and timeline.
"""

from pathlib import Path
from uuid import UUID

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

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
    """Placeholder landing page for Doctor users."""
    return _role_home(request, "Doctor")


@login_required  # type: ignore[untyped-decorator]
@require_GET  # type: ignore[untyped-decorator]
def scheduler_home(request: HttpRequest) -> HttpResponse:
    """Placeholder landing page for Scheduler users."""
    return _role_home(request, "Scheduler")


@login_required  # type: ignore[untyped-decorator]
@require_GET  # type: ignore[untyped-decorator]
def manager_home(request: HttpRequest) -> HttpResponse:
    """Placeholder landing page for Manager users."""
    return _role_home(request, "Manager")


@login_required  # type: ignore[untyped-decorator]
@require_GET  # type: ignore[untyped-decorator]
def admin_home(request: HttpRequest) -> HttpResponse:
    """Placeholder landing page for Admin users."""
    return _role_home(request, "Admin")


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
